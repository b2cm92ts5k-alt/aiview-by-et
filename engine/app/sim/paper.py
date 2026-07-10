"""Paper live-sim (TDD.md §7 / ARCHITECTURE data flow ข้อ 6b):

ทุก Signal ใหม่จาก /analyze → เปิดไม้จำลองอัตโนมัติ → ติดตาม candle stream
จนชน SL/TP/timeout → persist Trade + broadcast trade.update ทาง WS.
"""

from __future__ import annotations

import asyncio
import contextlib
import sqlite3
from collections.abc import Awaitable, Callable
from typing import Any

from app.data.service import DataService
from app.models import Signal, SimConfig, Trade
from app.sim import fill
from app.store import db

Broadcast = Callable[[str, dict[str, Any]], Awaitable[None]]


class PaperEngine:
    def __init__(
        self,
        service: DataService,
        conn: sqlite3.Connection,
        broadcast: Broadcast,
        config: SimConfig | None = None,
    ) -> None:
        self._service = service
        self._conn = conn
        self._broadcast = broadcast
        self._config = config or SimConfig()
        self._tasks: set[asyncio.Task[None]] = set()

    @property
    def open_count(self) -> int:
        return len(self._tasks)

    async def open_from_signal(self, signal: Signal) -> Trade:
        trade = fill.open_trade(signal, self._config)
        db.save_trade(self._conn, trade.model_dump(), source="paper")
        await self._broadcast("trade.update", trade.model_dump())
        task = asyncio.create_task(self._watch(trade))
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)
        return trade

    async def _watch(self, trade: Trade) -> None:
        bars_open = 0
        last_ts: int | None = None
        try:
            async for candle in self._service.stream(trade.symbol, trade.tf):
                if last_ts is not None and candle.ts > last_ts:
                    bars_open += 1  # นับเฉพาะแท่งใหม่ ไม่ใช่ update ของแท่งเดิม
                last_ts = candle.ts
                exit_info = fill.check_exit(trade, candle, bars_open, self._config)
                if exit_info:
                    price, kind = exit_info
                    closed = fill.close_trade(trade, price, kind, candle.ts, self._config)
                    db.save_trade(self._conn, closed.model_dump(), source="paper")
                    await self._broadcast("trade.update", closed.model_dump())
                    return
        except asyncio.CancelledError:
            raise
        except Exception as e:  # stream ล่ม — ไม้ยัง open, log ไว้
            with contextlib.suppress(Exception):
                await self._broadcast(
                    "engine.log",
                    {"level": "error", "msg": f"paper watch {trade.id} failed: {e}"},
                )

    async def close(self) -> None:
        for task in list(self._tasks):
            task.cancel()
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)
