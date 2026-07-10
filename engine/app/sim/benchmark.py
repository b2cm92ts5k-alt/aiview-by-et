"""In-app model benchmark (AI_MODELS.md §D — ผู้ใช้เคาะ 2026-07-10: ทำ).

Walk-forward: แบ่ง historical เป็น K จุดตัด — แต่ละ model เห็น candles ถึงจุดตัด
→ ออก signal → simulate บนแท่งถัดไปด้วย fill model เดียวกับ backtest →
เทียบ winrate/PF ต่อ model ด้วยข้อมูลชุดเดียวกัน ("แนะนำ" มีข้อมูลจริงรองรับ).
"""

from __future__ import annotations

import uuid
from collections.abc import Awaitable, Callable
from typing import Literal

from pydantic import BaseModel

from app.ai import orchestrator
from app.ai.base import AIProvider
from app.models import Candle, SimConfig, Stats, Timeframe, Trade
from app.sim import fill
from app.sim.stats import compute_stats

MIN_HISTORY_BARS = 120  # ต้องมีพอให้ indicator นิ่งก่อนจุดตัดแรก


class BenchmarkModelRef(BaseModel):
    provider: str
    model: str


class BenchmarkRequest(BaseModel):
    models: list[BenchmarkModelRef]
    symbol: str = "BTC/USDT"
    tf: Timeframe = "15m"
    limit: int = 800  # แท่ง historical ทั้งหมด
    windows: int = 6  # จำนวนจุดตัด (= จำนวนครั้งที่เรียก AI ต่อ model)
    config: SimConfig = SimConfig()


class BenchmarkModelResult(BaseModel):
    provider: str
    model: str
    signals: int
    no_setup: int
    errors: int
    stats: Stats


class BenchmarkRun(BaseModel):
    run_id: str
    status: Literal["running", "done", "error"]
    progress: float
    detail: str | None = None
    results: list[BenchmarkModelResult] = []


async def run_benchmark(
    req: BenchmarkRequest,
    providers: dict[str, AIProvider],
    candles: list[Candle],
    on_progress: Callable[[float], Awaitable[None]] | None = None,
) -> list[BenchmarkModelResult]:
    if len(candles) < MIN_HISTORY_BARS + req.windows:
        raise ValueError("not enough history for benchmark")

    # จุดตัด K จุด กระจายเท่าๆ กันหลัง warm-up
    span = len(candles) - MIN_HISTORY_BARS - 1
    cuts = [MIN_HISTORY_BARS + (span * (i + 1)) // (req.windows + 1)
            for i in range(req.windows)]

    results: list[BenchmarkModelResult] = []
    total_steps = len(req.models) * len(cuts)
    step = 0

    for ref in req.models:
        provider = providers.get(ref.provider)
        if provider is None:
            raise KeyError(f"unknown AI provider: {ref.provider}")
        trades: list[Trade] = []
        no_setup = 0
        errors = 0
        for cut in cuts:
            step += 1
            visible = candles[:cut]
            try:
                signal = await orchestrator.analyze_prepared(
                    provider, ref.model, req.symbol, req.tf, visible
                )
                trade = fill.open_trade(signal, req.config,
                                        opened_at=visible[-1].ts)
                for bars_open, i in enumerate(range(cut, len(candles)), start=1):
                    exit_info = fill.check_exit(trade, candles[i], bars_open, req.config)
                    if exit_info:
                        price, kind = exit_info
                        trade = fill.close_trade(trade, price, kind,
                                                 candles[i].ts, req.config)
                        break
                trades.append(trade)
            except orchestrator.NoSetupError:
                no_setup += 1
            except Exception:
                errors += 1
            if on_progress:
                await on_progress(step / total_steps)

        results.append(BenchmarkModelResult(
            provider=ref.provider,
            model=ref.model,
            signals=len(trades),
            no_setup=no_setup,
            errors=errors,
            stats=compute_stats(trades, req.config,
                                scope=f"benchmark:{ref.provider}:{ref.model}"),
        ))
    return results


class BenchmarkRegistry:
    def __init__(self) -> None:
        self._runs: dict[str, BenchmarkRun] = {}

    def create(self) -> str:
        run_id = str(uuid.uuid4())
        self._runs[run_id] = BenchmarkRun(run_id=run_id, status="running", progress=0.0)
        return run_id

    def progress(self, run_id: str, value: float) -> None:
        run = self._runs.get(run_id)
        if run:
            run.progress = round(value, 4)

    def finish(self, run_id: str, results: list[BenchmarkModelResult]) -> None:
        self._runs[run_id] = BenchmarkRun(run_id=run_id, status="done", progress=1.0,
                                          results=results)

    def fail(self, run_id: str, detail: str) -> None:
        self._runs[run_id] = BenchmarkRun(run_id=run_id, status="error", progress=1.0,
                                          detail=detail)

    def get(self, run_id: str) -> BenchmarkRun | None:
        return self._runs.get(run_id)
