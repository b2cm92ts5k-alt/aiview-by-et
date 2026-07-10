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
from app.models import AnalyzeRequest, Candle, MarketsResponse, Signal, Timeframe
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

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        yield
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
        return signal

    @app.get("/signals")
    def signals(symbol: str | None = None, limit: int = Query(default=100, ge=1, le=500)
                ) -> list[Signal]:
        return [Signal(**p) for p in db.list_signals(conn, symbol, limit)]

    @app.websocket("/ws")
    async def ws(websocket: WebSocket) -> None:
        if token and websocket.query_params.get("token") != token:
            await websocket.close(code=4401)
            return
        await websocket.accept()
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
            stop_stream()

    return app


def _envelope(type_: str, payload: dict[str, Any]) -> dict[str, Any]:
    return {"type": type_, "ts": int(time.time() * 1000), "payload": payload}
