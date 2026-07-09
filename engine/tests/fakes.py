"""Deterministic fake DataProvider for tests — no network."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator

from app.data.base import Capabilities, DataProvider
from app.data.timeframes import TF_MS
from app.models import Candle, SymbolInfo, Timeframe

BASE_TS = 1_700_000_100_000  # arbitrary fixed epoch ms (not tf-aligned)


def make_candles(symbol: str, tf: Timeframe, n: int, start: int | None = None) -> list[Candle]:
    width = TF_MS[tf]
    t0 = start if start is not None else (BASE_TS // width) * width
    out = []
    for i in range(n):
        o = 100.0 + i
        out.append(
            Candle(symbol=symbol, tf=tf, ts=t0 + i * width,
                   o=o, h=o + 2, l=o - 1, c=o + 1, v=10.0)
        )
    return out


class FakeProvider(DataProvider):
    name = "fake"

    # 10m/45m/1Y intentionally absent → forces the resample path
    NATIVE: list[Timeframe] = ["5m", "15m", "30m", "60m", "4h", "1D", "1W", "1M"]

    def __init__(self, stream_candles: list[Candle] | None = None):
        self.stream_candles = stream_candles or []
        self.fetch_calls: list[tuple[str, Timeframe, int]] = []

    def capabilities(self) -> Capabilities:
        return Capabilities(timeframes=self.NATIVE, realtime=True)

    async def list_symbols(self) -> list[SymbolInfo]:
        return [
            SymbolInfo(symbol="BTC/USDT", name="BTC", asset_class="crypto", provider=self.name),
            SymbolInfo(symbol="ETH/USDT", name="ETH", asset_class="crypto", provider=self.name),
        ]

    async def fetch_ohlcv(
        self, symbol: str, tf: Timeframe, since: int | None = None, limit: int = 500
    ) -> list[Candle]:
        self.fetch_calls.append((symbol, tf, limit))
        return make_candles(symbol, tf, min(limit, 24))

    async def subscribe(self, symbol: str, tf: Timeframe) -> AsyncIterator[Candle]:
        for c in self.stream_candles:
            yield c
        await asyncio.Event().wait()  # stay alive like a real stream
