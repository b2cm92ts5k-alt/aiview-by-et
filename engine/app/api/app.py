"""FastAPI app factory.

Auth model (TDD.md §2): engine binds loopback only; every request except
GET /health must carry the per-session token (X-Engine-Token header, or
?token= for WebSocket) that Electron main generated at spawn time.
"""

from __future__ import annotations

import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app import __version__
from app.store import db

HEALTH_PATH = "/health"


def create_app(db_path: str, token: str | None = None) -> FastAPI:
    conn = db.connect(db_path)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        yield
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

    @app.websocket("/ws")
    async def ws(websocket: WebSocket) -> None:
        if token and websocket.query_params.get("token") != token:
            await websocket.close(code=4401)
            return
        await websocket.accept()
        await websocket.send_json(_envelope("engine.hello", {"version": __version__}))
        try:
            while True:
                # M0: keepalive echo only; M1 pushes candle.update etc. (TDD §3.3)
                msg = await websocket.receive_text()
                if msg == "ping":
                    await websocket.send_json(_envelope("pong", {}))
        except Exception:
            pass

    return app


def _envelope(type_: str, payload: dict[str, Any]) -> dict[str, Any]:
    return {"type": type_, "ts": int(time.time() * 1000), "payload": payload}
