"""FastAPI app factory.

Auth model (TDD.md §2): engine binds loopback only; every request except
GET /health must carry the per-session token (X-Engine-Token header, or
?token= for WebSocket) that Electron main generated at spawn time.
"""

from __future__ import annotations

import asyncio
import os
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException, Query, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app import __version__
from app.ai import orchestrator
from app.ai.base import AIProvider
from app.data.service import DataService
from app.indicators.base import IndicatorResult, candles_to_df
from app.indicators.registry import SETS
from app.models import (
    AnalyzeRequest,
    BacktestRequest,
    BacktestRun,
    Candle,
    MarketsResponse,
    Signal,
    SimConfig,
    Stats,
    Timeframe,
    Trade,
)
from app.sim import backtest as bt
from app.sim.paper import PaperEngine
from app.sim.stats import compute_stats
from app.store import db

HEALTH_PATH = "/health"


def build_default_service() -> DataService:
    from app.data.base import DataProvider
    from app.data.binance import BinanceProvider

    providers: list[DataProvider] = [BinanceProvider()]
    td_key = os.environ.get("TWELVEDATA_API_KEY")
    if td_key:
        from app.data.twelvedata import TwelveDataProvider

        providers.append(TwelveDataProvider(td_key))
    return DataService(providers)


def build_default_ai_providers() -> dict[str, AIProvider]:
    from app.ai.ollama import OllamaProvider

    # cloud providers (Anthropic/OpenAI/...) มาเฟส M5 — key-gated ผ่าน vault
    return {"ollama": OllamaProvider()}


def create_app(
    db_path: str,
    token: str | None = None,
    data_service: DataService | None = None,
    ai_providers: dict[str, AIProvider] | None = None,
) -> FastAPI:
    conn = db.connect(db_path)
    service = data_service or build_default_service()
    ai = ai_providers if ai_providers is not None else build_default_ai_providers()

    ws_clients: set[WebSocket] = set()

    async def broadcast(type_: str, payload: dict[str, Any]) -> None:
        msg = _envelope(type_, payload)
        for client in list(ws_clients):
            try:
                await client.send_json(msg)
            except Exception:
                ws_clients.discard(client)

    paper = PaperEngine(service, conn, broadcast)
    runs = bt.RunRegistry()

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        yield
        await paper.close()
        await service.close()
        for p in ai.values():
            await p.close()
        conn.close()

    app = FastAPI(title="AIView Engine", version=__version__, lifespan=lifespan)

    # Renderer calls the engine from an http origin (Vite dev) or file://;
    # loopback bind + session token is the real boundary, CORS just unblocks fetch.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.state.db = conn

    @app.middleware("http")
    async def require_token(request: Request, call_next: Any) -> Any:
        if token and request.url.path != HEALTH_PATH and request.method != "OPTIONS":
            if request.headers.get("X-Engine-Token") != token:
                return JSONResponse(status_code=401, content={"detail": "invalid engine token"})
        return await call_next(request)

    @app.get(HEALTH_PATH)
    def health() -> dict[str, str]:
        return {"status": "ok", "version": __version__}

    @app.get("/settings")
    def get_settings() -> dict[str, Any]:
        return db.get_settings(conn)

    @app.put("/settings")
    def put_settings(patch: dict[str, Any]) -> dict[str, Any]:
        return db.put_settings(conn, patch)

    @app.get("/markets")
    async def markets() -> MarketsResponse:
        return await service.markets()

    @app.get("/candles")
    async def candles(
        symbol: str,
        tf: Timeframe,
        since: int | None = None,
        limit: int = Query(default=500, ge=1, le=5000),
    ) -> list[Candle]:
        try:
            return await service.candles(symbol, tf, since=since, limit=limit)
        except KeyError as e:
            raise HTTPException(status_code=404, detail=str(e)) from e

    @app.get("/indicators")
    async def indicators(
        symbol: str,
        tf: Timeframe,
        set: str = "core",
        limit: int = Query(default=500, ge=50, le=5000),
    ) -> list[IndicatorResult]:
        compute = SETS.get(set)
        if compute is None:
            raise HTTPException(status_code=404, detail=f"unknown indicator set: {set}")
        try:
            data = await service.candles(symbol, tf, limit=limit)
        except KeyError as e:
            raise HTTPException(status_code=404, detail=str(e)) from e
        return compute(candles_to_df(data))

    @app.get("/ai/models")
    async def ai_models(provider: str | None = None) -> dict[str, list[str]]:
        # key-gated (F7): เฉพาะ provider ที่พร้อมใช้เท่านั้นที่ถูก register
        selected = {provider: ai[provider]} if provider and provider in ai else ai
        return {name: await p.list_models() for name, p in selected.items()}

    @app.post("/analyze")
    async def analyze(req: AnalyzeRequest) -> Signal | None:
        """คืน Signal หรือ null เมื่อ AI เห็นว่าไม่มี setup (ไม่ใช่ error)."""
        provider = ai.get(req.provider)
        if provider is None:
            raise HTTPException(status_code=404, detail=f"unknown AI provider: {req.provider}")
        if not req.tfs:
            raise HTTPException(status_code=422, detail="tfs must not be empty")
        try:
            signal = await orchestrator.analyze(service, provider, req.model,
                                                req.symbol, req.tfs)
        except KeyError as e:
            raise HTTPException(status_code=404, detail=str(e)) from e
        except orchestrator.NoSetupError:
            return None
        except orchestrator.SignalParseError as e:
            raise HTTPException(status_code=502, detail=f"AI response invalid: {e}") from e
        db.save_signal(conn, signal.id, signal.symbol, signal.tf,
                       signal.created_at, signal.model_dump())
        await broadcast("signal.new", signal.model_dump())
        # ARCHITECTURE data flow 6b: signal ใหม่ → simulator เปิดไม้จำลองทันที
        await paper.open_from_signal(signal)
        return signal

    @app.get("/signals")
    def signals(symbol: str | None = None, limit: int = Query(default=100, ge=1, le=500)
                ) -> list[Signal]:
        return [Signal(**p) for p in db.list_signals(conn, symbol, limit)]

    @app.post("/sim/backtest")
    async def sim_backtest(req: BacktestRequest) -> dict[str, str]:
        run_id = runs.create()

        async def execute() -> None:
            try:
                candles = await service.candles(req.symbol, req.tf, limit=req.limit)
                trades, stats = bt.run_backtest(candles, req.config, req.strategy)
                for t in trades:
                    db.save_trade(conn, t.model_dump(), source="backtest", run_id=run_id)
                db.save_sim_run(conn, run_id, int(time.time() * 1000),
                                req.model_dump(), stats.model_dump(exclude={"equity_curve"}))
                runs.finish(run_id, trades, stats)
                await broadcast("sim.progress", {"run_id": run_id, "status": "done"})
            except Exception as e:
                runs.fail(run_id, str(e))
                await broadcast("sim.progress", {"run_id": run_id, "status": "error",
                                                 "detail": str(e)})

        asyncio.create_task(execute())
        return {"run_id": run_id}

    @app.get("/sim/runs/{run_id}")
    def sim_run(run_id: str) -> BacktestRun:
        run = runs.get(run_id)
        if run is None:
            raise HTTPException(status_code=404, detail=f"unknown run: {run_id}")
        return run

    @app.get("/trades")
    def trades(
        scope: str | None = Query(default=None, pattern="^(backtest|paper)$"),
        symbol: str | None = None,
        run_id: str | None = None,
        limit: int = Query(default=500, ge=1, le=5000),
    ) -> list[Trade]:
        return [Trade(**t) for t in db.list_trades(conn, scope, symbol, run_id, limit)]

    @app.get("/stats")
    def stats(
        scope: str | None = Query(default=None, pattern="^(backtest|paper)$"),
        symbol: str | None = None,
        run_id: str | None = None,
    ) -> Stats:
        rows = [Trade(**t) for t in db.list_trades(conn, scope, symbol, run_id, limit=5000)]
        return compute_stats(rows, SimConfig(), scope=scope or "all")

    @app.websocket("/ws")
    async def ws(websocket: WebSocket) -> None:
        if token and websocket.query_params.get("token") != token:
            await websocket.close(code=4401)
            return
        await websocket.accept()
        ws_clients.add(websocket)
        await websocket.send_json(_envelope("engine.hello", {"version": __version__}))

        stream_task: asyncio.Task[None] | None = None

        async def run_stream(symbol: str, tf: Timeframe) -> None:
            try:
                async for candle in service.stream(symbol, tf):
                    await websocket.send_json(
                        _envelope("candle.update", candle.model_dump())
                    )
            except asyncio.CancelledError:
                raise
            except Exception as e:  # provider/network error → tell client, keep socket
                await websocket.send_json(
                    _envelope("stream.error", {"symbol": symbol, "tf": tf, "detail": str(e)})
                )

        def stop_stream() -> None:
            nonlocal stream_task
            if stream_task is not None:
                stream_task.cancel()
                stream_task = None

        try:
            while True:
                msg = await websocket.receive_json()
                mtype = msg.get("type")
                payload = msg.get("payload") or {}
                if mtype == "ping":
                    await websocket.send_json(_envelope("pong", {}))
                elif mtype == "subscribe":
                    stop_stream()
                    stream_task = asyncio.create_task(
                        run_stream(payload["symbol"], payload["tf"])
                    )
                elif mtype == "unsubscribe":
                    stop_stream()
        except WebSocketDisconnect:
            pass
        finally:
            ws_clients.discard(websocket)
            stop_stream()

    return app


def _envelope(type_: str, payload: dict[str, Any]) -> dict[str, Any]:
    return {"type": type_, "ts": int(time.time() * 1000), "payload": payload}
