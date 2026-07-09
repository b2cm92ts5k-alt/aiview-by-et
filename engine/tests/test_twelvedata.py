import httpx
import pytest

from app.data.twelvedata import TwelveDataProvider


def _client(handler: httpx.MockTransport) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=handler, base_url="https://api.twelvedata.com")


@pytest.mark.anyio
async def test_fetch_ohlcv_parses_and_sorts_oldest_first() -> None:
    def handle(request: httpx.Request) -> httpx.Response:
        assert request.url.params["symbol"] == "XAU/USD"
        assert request.url.params["interval"] == "1h"
        return httpx.Response(200, json={
            "values": [  # TD ส่ง newest-first
                {"datetime": "2026-07-10 11:00:00", "open": "2.0", "high": "2.5",
                 "low": "1.8", "close": "2.2", "volume": "100"},
                {"datetime": "2026-07-10 10:00:00", "open": "1.0", "high": "1.5",
                 "low": "0.8", "close": "1.2", "volume": "50"},
            ],
            "status": "ok",
        })

    provider = TwelveDataProvider("k", client=_client(httpx.MockTransport(handle)))
    candles = await provider.fetch_ohlcv("XAU/USD", "60m")
    assert len(candles) == 2
    assert candles[0].ts < candles[1].ts
    assert candles[0].o == 1.0 and candles[1].c == 2.2
    assert candles[0].tf == "60m"


@pytest.mark.anyio
async def test_error_status_raises() -> None:
    def handle(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"status": "error", "message": "invalid api key"})

    provider = TwelveDataProvider("bad", client=_client(httpx.MockTransport(handle)))
    with pytest.raises(RuntimeError, match="invalid api key"):
        await provider.fetch_ohlcv("XAU/USD", "60m")


@pytest.mark.anyio
async def test_daily_datetime_format_parsed() -> None:
    def handle(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={
            "values": [{"datetime": "2026-07-09", "open": "1", "high": "2",
                        "low": "0.5", "close": "1.5"}],
            "status": "ok",
        })

    provider = TwelveDataProvider("k", client=_client(httpx.MockTransport(handle)))
    candles = await provider.fetch_ohlcv("AAPL", "1D")
    assert candles[0].v == 0.0  # volume optional
    assert candles[0].ts % 86_400_000 == 0


def test_capabilities_no_10m_no_1y() -> None:
    provider = TwelveDataProvider("k")
    tfs = provider.capabilities().timeframes
    assert "10m" not in tfs and "1Y" not in tfs
    assert "45m" in tfs  # TD มี 45min ตรงๆ
