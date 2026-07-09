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
from app.data.service import DataService
from app.models import Candle, MarketsResponse, Timeframe
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


def create_app(
    db_path: str,
    token: str | None = None,
    data_service: DataService | None = None,
) -> FastAPI:
    conn = db.connect(db_path)
    service = data_service or build_default_service()

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        yield
        await service.close()
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
