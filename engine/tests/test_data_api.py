from fastapi.testclient import TestClient

from app.api.app import create_app
from app.data.service import DataService
from app.data.timeframes import TF_MS

from .fakes import FakeProvider, make_candles


def test_markets_lists_fake_symbols(client: TestClient) -> None:
    res = client.get("/markets")
    assert res.status_code == 200
    body = res.json()
    assert body["asset_classes"] == ["crypto"]
    symbols = [s["symbol"] for s in body["symbols"]]
    assert "BTC/USDT" in symbols and "ETH/USDT" in symbols


def test_candles_native_tf(client: TestClient) -> None:
    res = client.get("/candles", params={"symbol": "BTC/USDT", "tf": "5m", "limit": 10})
    assert res.status_code == 200
    candles = res.json()
    assert len(candles) == 10
    assert candles[0]["tf"] == "5m"
    assert candles[0]["ts"] % TF_MS["5m"] == 0


def test_candles_resampled_tf(client: TestClient, fake_provider: FakeProvider) -> None:
    res = client.get("/candles", params={"symbol": "BTC/USDT", "tf": "10m", "limit": 5})
    assert res.status_code == 200
    candles = res.json()
    assert all(c["tf"] == "10m" for c in candles)
    assert all(c["ts"] % TF_MS["10m"] == 0 for c in candles)
    # service ต้องขอ base 5m จาก provider ไม่ใช่ 10m ตรงๆ
    assert fake_provider.fetch_calls[-1][1] == "5m"


def test_candles_unknown_symbol_404(client: TestClient) -> None:
    res = client.get("/candles", params={"symbol": "NOPE/USDT", "tf": "5m"})
    assert res.status_code == 404


def test_candles_invalid_tf_422(client: TestClient) -> None:
    res = client.get("/candles", params={"symbol": "BTC/USDT", "tf": "7m"})
    assert res.status_code == 422


def test_ws_subscribe_streams_candle_updates(db_path: str) -> None:
    stream = make_candles("BTC/USDT", "5m", 3)
    provider = FakeProvider(stream_candles=stream)
    app = create_app(db_path, data_service=DataService([provider]))
    with TestClient(app) as client:
        with client.websocket_connect("/ws") as ws:
            assert ws.receive_json()["type"] == "engine.hello"
            ws.send_json({"type": "subscribe", "payload": {"symbol": "BTC/USDT", "tf": "5m"}})
            msgs = [ws.receive_json() for _ in range(3)]
            assert all(m["type"] == "candle.update" for m in msgs)
            assert [m["payload"]["ts"] for m in msgs] == [c.ts for c in stream]
            assert msgs[0]["payload"]["symbol"] == "BTC/USDT"


def test_ws_subscribe_resampled_tf(db_path: str) -> None:
    t0 = (1_700_000_100_000 // TF_MS["10m"]) * TF_MS["10m"]
    stream = make_candles("BTC/USDT", "5m", 2, start=t0)  # สอง base bars → bucket 10m เดียวกัน
    provider = FakeProvider(stream_candles=stream)
    app = create_app(db_path, data_service=DataService([provider]))
    with TestClient(app) as client:
        with client.websocket_connect("/ws") as ws:
            ws.receive_json()  # hello
            ws.send_json({"type": "subscribe", "payload": {"symbol": "BTC/USDT", "tf": "10m"}})
            m1 = ws.receive_json()
            m2 = ws.receive_json()
            assert m1["payload"]["tf"] == "10m"
            assert m1["payload"]["ts"] == m2["payload"]["ts"]  # bucket เดียวกัน
            assert m2["payload"]["v"] == stream[0].v + stream[1].v
