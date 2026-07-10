"""Binance provider via ccxt (DATA_SOURCES.md §5: crypto หลัก, ฟรี ไม่ต้องมี key).

Uses ccxt's unified API — REST fetch_ohlcv for history, ccxt.pro watch_ohlcv
(public WebSocket kline stream) for realtime. No credentials required for
public market data.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

import aiohttp
import ccxt.pro as ccxtpro

from app.data.base import Capabilities, DataProvider
from app.models import Candle, SymbolInfo, Timeframe

# app tf → ccxt tf (only tfs Binance serves natively; 10m/45m/1Y are resampled upstream)
CCXT_TF: dict[Timeframe, str] = {
    "5m": "5m",
    "15m": "15m",
    "30m": "30m",
    "60m": "1h",
    "4h": "4h",
    "1D": "1d",
    "1W": "1w",
    "1M": "1M",
}

# curated watchlist defaults — full search hits load_markets()
DEFAULT_SYMBOLS = ["BTC/USDT", "ETH/USDT", "BNB/USDT", "SOL/USDT", "XRP/USDT", "DOGE/USDT"]


def _to_candle(symbol: str, tf: Timeframe, row: list[Any]) -> Candle:
    ts, o, h, low, c, v = row[:6]
    return Candle(symbol=symbol, tf=tf, ts=int(ts), o=o, h=h, l=low, c=c, v=v or 0.0)


class BinanceProvider(DataProvider):
    name = "binance"

    def __init__(self) -> None:
        self._exchange: ccxtpro.binance = ccxtpro.binance({"enableRateLimit": True})
        self._session: aiohttp.ClientSession | None = None

    async def _ensure_session(self) -> None:
        """Force aiohttp's ThreadedResolver (OS getaddrinfo).

        The default aiodns/c-ares resolver does raw UDP DNS queries which fail
        on some Windows setups/networks ("Could not contact DNS servers").
        Must run inside the event loop, hence lazy not __init__.
        """
        if self._session is None:
            self._session = aiohttp.ClientSession(
                connector=aiohttp.TCPConnector(resolver=aiohttp.ThreadedResolver())
            )
            self._exchange.session = self._session

    def capabilities(self) -> Capabilities:
        return Capabilities(timeframes=list(CCXT_TF.keys()), realtime=True)

    async def list_symbols(self) -> list[SymbolInfo]:
        await self._ensure_session()
        markets = await self._exchange.load_markets()
        out: list[SymbolInfo] = []
        for sym, m in markets.items():
            if m.get("spot") and m.get("active") and m.get("quote") == "USDT":
                out.append(SymbolInfo(symbol=sym, name=m.get("base"), asset_class="crypto",
                                      provider=self.name))
        # curated defaults first, then the rest alphabetically
        order = {s: i for i, s in enumerate(DEFAULT_SYMBOLS)}
        out.sort(key=lambda s: (order.get(s.symbol, len(order)), s.symbol))
        return out

    async def fetch_ohlcv(
        self, symbol: str, tf: Timeframe, since: int | None = None, limit: int = 500
    ) -> list[Candle]:
        await self._ensure_session()
        rows = await self._exchange.fetch_ohlcv(symbol, CCXT_TF[tf], since=since, limit=limit)
        return [_to_candle(symbol, tf, r) for r in rows]

    async def subscribe(self, symbol: str, tf: Timeframe) -> AsyncIterator[Candle]:
        await self._ensure_session()
        while True:
            rows = await self._exchange.watch_ohlcv(symbol, CCXT_TF[tf])
            for r in rows:
                yield _to_candle(symbol, tf, r)

    async def close(self) -> None:
        await self._exchange.close()
        if self._session is not None:
            await self._session.close()
