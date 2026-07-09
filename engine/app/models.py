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
