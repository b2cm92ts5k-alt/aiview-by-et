"""Backtest engine (TDD.md §7): replay signals over historical candles → Trade[].

POST /sim/backtest is async per TDD §3.2 — runs registry keeps status/progress;
finished trades are persisted by the API layer.
"""

from __future__ import annotations

import uuid

from app.models import BacktestRun, Candle, Signal, SimConfig, Stats, Trade
from app.sim import fill, strategy
from app.sim.stats import compute_stats


def run_backtest(
    candles: list[Candle],
    config: SimConfig,
    strategy_name: str = "zlema-smc",
    signals: list[Signal] | None = None,
) -> tuple[list[Trade], Stats]:
    """signals=None → generate จาก rule strategy; ส่ง signals มาเอง = replay โหมด."""
    sigs = signals if signals is not None else strategy.generate_signals(candles, strategy_name)
    ts_to_idx = {c.ts: i for i, c in enumerate(candles)}

    trades: list[Trade] = []
    for sig in sigs:
        start = ts_to_idx.get(sig.created_at)
        if start is None or start + 1 >= len(candles):
            continue
        trade = fill.open_trade(sig, config, opened_at=sig.created_at)
        # เดินแท่งถัดจาก signal จนออก
        for bars_open, i in enumerate(range(start + 1, len(candles)), start=1):
            exit_info = fill.check_exit(trade, candles[i], bars_open, config)
            if exit_info:
                price, kind = exit_info
                trade = fill.close_trade(trade, price, kind, candles[i].ts, config)
                break
        trades.append(trade)  # ไม้ที่ไม่ปิด = สถานะ open ค้าง (ข้อมูลหมดก่อน)

    stats = compute_stats(trades, config, scope="backtest")
    return trades, stats


class RunRegistry:
    """in-memory async run tracking — {run_id: BacktestRun}."""

    def __init__(self) -> None:
        self._runs: dict[str, BacktestRun] = {}

    def create(self) -> str:
        run_id = str(uuid.uuid4())
        self._runs[run_id] = BacktestRun(run_id=run_id, status="running", progress=0.0)
        return run_id

    def finish(self, run_id: str, trades: list[Trade], stats: Stats) -> None:
        self._runs[run_id] = BacktestRun(
            run_id=run_id, status="done", progress=1.0, trades=trades, stats=stats,
        )

    def fail(self, run_id: str, detail: str) -> None:
        self._runs[run_id] = BacktestRun(
            run_id=run_id, status="error", progress=1.0, detail=detail,
        )

    def get(self, run_id: str) -> BacktestRun | None:
        return self._runs.get(run_id)
