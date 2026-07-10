from fastapi.testclient import TestClient


def test_indicators_core_set(client: TestClient) -> None:
    res = client.get("/indicators", params={"symbol": "BTC/USDT", "tf": "5m", "limit": 60})
    assert res.status_code == 200
    body = res.json()
    names = {r["name"] for r in body}
    assert names == {"ema", "rsi", "atr", "macd", "zero_lag", "smc"}
    ema = next(r for r in body if r["name"] == "ema")
    # ค่า line ยาวเท่ากับจำนวนแท่งที่ขอ (FakeProvider คืนตาม limit, cap 400)
    assert len(ema["lines"]["ema20"]) == 60
    assert ema["lines"]["ema20"][-1] is not None


def test_indicators_unknown_set_404(client: TestClient) -> None:
    res = client.get(
        "/indicators", params={"symbol": "BTC/USDT", "tf": "5m", "set": "nope", "limit": 60}
    )
    assert res.status_code == 404


def test_indicators_unknown_symbol_404(client: TestClient) -> None:
    res = client.get("/indicators", params={"symbol": "NOPE", "tf": "5m", "limit": 60})
    assert res.status_code == 404
