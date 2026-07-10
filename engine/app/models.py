"""Core domain models — mirror of ARCHITECTURE.md §5 (Candle) + §6 (timeframes).

packages/shared-types/src/index.ts must stay in sync until OpenAPI codegen lands.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

Timeframe = Literal["5m", "10m", "15m", "30m", "45m", "60m", "4h", "1D", "1W", "1M", "1Y"]

TIMEFRAMES: tuple[Timeframe, ...] = (
    "5m", "10m", "15m", "30m", "45m", "60m", "4h", "1D", "1W", "1M", "1Y",
)

AssetClass = Literal["crypto", "stock", "gold", "oil", "fx"]


class Candle(BaseModel):
    symbol: str
    tf: Timeframe
    ts: int  # bar open time, UTC epoch ms
    o: float
    h: float
    l: float  # noqa: E741 — schema field name locked in ARCHITECTURE.md §5
    c: float
    v: float


class SymbolInfo(BaseModel):
    symbol: str  # canonical app symbol, ccxt style for crypto ("BTC/USDT")
    name: str | None = None
    asset_class: AssetClass
    provider: str


class MarketsResponse(BaseModel):
    asset_classes: list[AssetClass]
    symbols: list[SymbolInfo]


Side = Literal["long", "short"]


class Signal(BaseModel):
    """FEATURES.md §F1 signal schema (core fields per ARCHITECTURE.md §5)."""

    id: str
    symbol: str
    tf: Timeframe  # primary tf the setup is based on
    side: Side
    entry: float
    sl: float
    tp: list[float]  # 1..3 targets
    rr: float
    confidence: int  # 0-100
    reason: str
    indicators_used: dict[str, str] = {}
    model: str
    position_size_hint: str | None = None
    leverage_hint: str | None = None
    created_at: int  # UTC ms
    valid_until: int | None = None


class AnalyzeRequest(BaseModel):
    symbol: str
    tfs: list[Timeframe] = ["15m", "60m", "4h"]  # first = primary
    provider: str = "ollama"
    model: str


class GenerateIndicatorRequest(BaseModel):
    """POST /indicators/ai/generate (F6)."""

    description: str
    provider: str = "ollama"
    model: str
    symbol: str = "BTC/USDT"  # sample data สำหรับ validate + quick backtest
    tf: Timeframe = "15m"


TradeStatus = Literal["open", "win", "loss", "be", "timeout"]


class Trade(BaseModel):
    """ARCHITECTURE.md §5 Trade schema."""

    id: str
    signal_id: str
    symbol: str
    tf: Timeframe
    side: Side
    entry: float
    exit: float | None = None
    sl: float
    tp: float  # TP1 — fill model v1 exits ทั้งไม้ที่ TP1 (spec.md Decisions 2026-07-10)
    qty: float
    pnl: float | None = None
    r_multiple: float | None = None
    status: TradeStatus = "open"
    model: str  # AI model ที่ออก signal (สำหรับ breakdown per-model)
    opened_at: int
    closed_at: int | None = None


class SimConfig(BaseModel):
    """ค่าจำลองการเทรด (F2) — ทั้งหมดผู้ใช้ปรับได้ ห้าม hardcode ในโค้ด."""

    initial_capital: float = 10_000.0
    risk_per_trade_pct: float = 1.0  # % ของทุนตั้งต้น (non-compounding)
    fee_pct: float = 0.04  # taker fee ต่อขา (%)
    slippage_pct: float = 0.01  # ต่อขา (%)
    timeout_bars: int = 96  # ปิดไม้ถ้าไม่ชน SL/TP ภายใน N แท่ง


class EquityPoint(BaseModel):
    ts: int
    equity: float


class StatsBreakdownRow(BaseModel):
    key: str  # เช่น "BTC/USDT", "15m", "qwen3:8b", "long"
    trades: int
    winrate: float
    avg_r: float
    pnl: float


class Stats(BaseModel):
    """ARCHITECTURE.md §5 Stats schema."""

    scope: str
    trades: int
    wins: int
    losses: int
    winrate: float  # 0-100
    avg_r: float
    expectancy: float  # avg R ต่อไม้ (รวมแพ้ชนะ)
    profit_factor: float
    max_drawdown_pct: float
    total_pnl: float
    equity_curve: list[EquityPoint]
    by_symbol: list[StatsBreakdownRow] = []
    by_tf: list[StatsBreakdownRow] = []
    by_model: list[StatsBreakdownRow] = []
    by_side: list[StatsBreakdownRow] = []


class BacktestRequest(BaseModel):
    symbol: str
    tf: Timeframe = "15m"
    limit: int = 1000  # จำนวนแท่ง historical
    strategy: str = "zlema-smc"
    config: SimConfig = SimConfig()


class BacktestRun(BaseModel):
    run_id: str
    status: Literal["running", "done", "error"]
    progress: float  # 0-1
    detail: str | None = None
    trades: list[Trade] | None = None
    stats: Stats | None = None
