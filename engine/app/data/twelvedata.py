"""Twelve Data provider (DATA_SOURCES.md §5: non-crypto หลัก — stocks/gold/oil/FX).

BYOK: key comes from env TWELVEDATA_API_KEY (dev) — vault→engine in-memory
handoff lands with the key-management UI (M5). Without a key the provider is
not registered and non-crypto symbols simply don't appear in /markets.

Free tier has no usable WS → realtime = polling (TDD §4: "ไม่งั้น poll").
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from datetime import UTC
from typing import Any

import httpx

from app.data.base import Capabilities, DataProvider
from app.data.timeframes import TF_MS
from app.models import Candle, SymbolInfo, Timeframe

BASE_URL = "https://api.twelvedata.com"
POLL_SECONDS = 15.0

# app tf → Twelve Data interval (10m/1Y not offered → resampled upstream)
TD_INTERVAL: dict[Timeframe, str] = {
    "5m": "5min",
    "15m": "15min",
    "30m": "30min",
    "45m": "45min",
    "60m": "1h",
    "4h": "4h",
    "1D": "1day",
    "1W": "1week",
    "1M": "1month",
}

# symbol mapping ทอง/น้ำมัน/FX (DATA_SOURCES §6) — เริ่มชุดเล็ก เคาะเพิ่มได้
DEFAULT_SYMBOLS: list[SymbolInfo] = [
    SymbolInfo(symbol="XAU/USD", name="Gold", asset_class="gold", provider="twelvedata"),
    SymbolInfo(symbol="WTI/USD", name="WTI Crude Oil", asset_class="oil", provider="twelvedata"),
    SymbolInfo(symbol="BRN/USD", name="Brent Crude Oil", asset_class="oil", provider="twelvedata"),
    SymbolInfo(symbol="EUR/USD", name="Euro / US Dollar", asset_class="fx", provider="twelvedata"),
    SymbolInfo(symbol="USD/JPY", name="US Dollar / Yen", asset_class="fx", provider="twelvedata"),
    SymbolInfo(symbol="AAPL", name="Apple Inc.", asset_class="stock", provider="twelvedata"),
    SymbolInfo(symbol="TSLA", name="Tesla Inc.", asset_class="stock", provider="twelvedata"),
    SymbolInfo(symbol="NVDA", name="NVIDIA Corp.", asset_class="stock", provider="twelvedata"),
]


class TwelveDataProvider(DataProvider):
    name = "twelvedata"

    def __init__(self, api_key: str, client: httpx.AsyncClient | None = None) -> None:
        self._api_key = api_key
        self._client = client or httpx.AsyncClient(base_url=BASE_URL, timeout=15.0)

    def capabilities(self) -> Capabilities:
        return Capabilities(timeframes=list(TD_INTERVAL.keys()), realtime=False)

    async def list_symbols(self) -> list[SymbolInfo]:
        return list(DEFAULT_SYMBOLS)

    async def fetch_ohlcv(
        self, symbol: str, tf: Timeframe, since: int | None = None, limit: int = 500
    ) -> list[Candle]:
        params: dict[str, Any] = {
            "symbol": symbol,
            "interval": TD_INTERVAL[tf],
            "outputsize": min(limit, 5000),
            "apikey": self._api_key,
            "timezone": "UTC",
        }
        if since is not None:
            params["start_date"] = _iso_utc(since)
        res = await self._client.get("/time_series", params=params)
        res.raise_for_status()
        body = res.json()
        if body.get("status") == "error":
            raise RuntimeError(f"twelvedata: {body.get('message', 'unknown error')}")
        values = body.get("values", [])
        candles = [
            Candle(
                symbol=symbol,
                tf=tf,
                ts=_parse_ts(v["datetime"]),
                o=float(v["open"]),
                h=float(v["high"]),
                l=float(v["low"]),
                c=float(v["close"]),
                v=float(v.get("volume") or 0.0),
            )
            for v in values
        ]
        candles.sort(key=lambda c: c.ts)  # TD returns newest-first
        return candles

    async def subscribe(self, symbol: str, tf: Timeframe) -> AsyncIterator[Candle]:
        # free tier: poll the latest bar (delayed data acceptable — DATA_SOURCES §6)
        interval = POLL_SECONDS if tf in TF_MS else 60.0
        while True:
            candles = await self.fetch_ohlcv(symbol, tf, limit=1)
            if candles:
                yield candles[-1]
            await asyncio.sleep(interval)

    async def close(self) -> None:
        await self._client.aclose()


def _iso_utc(ts_ms: int) -> str:
    from datetime import datetime

    return datetime.fromtimestamp(ts_ms / 1000, tz=UTC).strftime("%Y-%m-%d %H:%M:%S")


def _parse_ts(value: str) -> int:
    from datetime import datetime

    fmt = "%Y-%m-%d %H:%M:%S" if " " in value else "%Y-%m-%d"
    return int(datetime.strptime(value, fmt).replace(tzinfo=UTC).timestamp() * 1000)
