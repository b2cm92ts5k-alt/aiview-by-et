"""Data service: routes symbols to providers and hides resampling.

Callers ask for any of the 11 app timeframes; if the provider lacks the tf
natively, history is resampled in batch and realtime is folded through
StreamAggregator (ARCHITECTURE.md §6, TDD §4).
"""

from __future__ import annotations

from collections.abc import AsyncIterator

from app.data.base import DataProvider
from app.data.resample import StreamAggregator, resample_candles
from app.data.timeframes import RESAMPLE_BASE
from app.models import Candle, MarketsResponse, SymbolInfo, Timeframe


class DataService:
    def __init__(self, providers: list[DataProvider]):
        self._providers = {p.name: p for p in providers}
        self._symbol_provider: dict[str, str] = {}
        self._symbols_cache: list[SymbolInfo] | None = None

    def add_provider(self, provider: DataProvider) -> None:
        """BYOK: register provider เพิ่ม runtime (เช่น TwelveData เมื่อผู้ใช้ใส่ key)."""
        self._providers[provider.name] = provider
        self._symbols_cache = None  # invalidate ให้ /markets โหลด symbol ใหม่
        self._symbol_provider = {}

    async def markets(self) -> MarketsResponse:
        if self._symbols_cache is None:
            symbols: list[SymbolInfo] = []
            for p in self._providers.values():
                symbols.extend(await p.list_symbols())
            self._symbols_cache = symbols
            self._symbol_provider = {s.symbol: s.provider for s in symbols}
        classes = sorted({s.asset_class for s in self._symbols_cache})
        return MarketsResponse(asset_classes=classes, symbols=self._symbols_cache)

    async def _resolve(self, symbol: str) -> DataProvider:
        if not self._symbol_provider:
            await self.markets()
        name = self._symbol_provider.get(symbol)
        if name is None:
            raise KeyError(f"unknown symbol: {symbol}")
        return self._providers[name]

    async def candles(
        self, symbol: str, tf: Timeframe, since: int | None = None, limit: int = 500
    ) -> list[Candle]:
        provider = await self._resolve(symbol)
        native = tf in provider.capabilities().timeframes
        if native:
            return await provider.fetch_ohlcv(symbol, tf, since=since, limit=limit)

        base = RESAMPLE_BASE[tf]
        # ~เผื่อ base bars ให้พอประกอบเป็น limit เป้าหมาย (10m=2×5m, 45m=3×15m, 1Y=12×1M)
        factor = {"10m": 2, "45m": 3, "1Y": 12}[tf]
        base_candles = await provider.fetch_ohlcv(symbol, base, since=since, limit=limit * factor)
        out = resample_candles(base_candles, tf)
        return out[-limit:]

    async def stream(self, symbol: str, tf: Timeframe) -> AsyncIterator[Candle]:
        provider = await self._resolve(symbol)
        native = tf in provider.capabilities().timeframes
        if native:
            async for candle in provider.subscribe(symbol, tf):
                yield candle
            return

        base = RESAMPLE_BASE[tf]
        agg = StreamAggregator(tf)
        async for base_candle in provider.subscribe(symbol, base):
            yield agg.push(base_candle)

    async def close(self) -> None:
        for p in self._providers.values():
            await p.close()
