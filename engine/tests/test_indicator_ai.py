import json

from fastapi.testclient import TestClient

from app.api.app import create_app
from app.data.service import DataService

from .fakes import FakeProvider
from .test_ai import FakeAI

GOOD_DEF = {
    "name": "zl_cross",
    "title": "ZLEMA Cross",
    "description": "zlema crossing sma marks momentum shift",
    "source": "Ehlers zero-lag EMA (public) + standard SMA",
    "params": {"fast": 9, "slow": 30},
    "lines": {"zl": "zlema(c, fast)", "base": "sma(c, slow)"},
    "long_when": "crossover(zl, base)",
    "short_when": "crossunder(zl, base)",
}


def make_client(db_path: str, ai: FakeAI) -> TestClient:
    return TestClient(create_app(
        db_path,
        data_service=DataService([FakeProvider()]),
        ai_providers={"ollama": ai},
    ))


def test_generate_validates_and_backtests(db_path: str) -> None:
    ai = FakeAI([json.dumps(GOOD_DEF)])
    with make_client(db_path, ai) as client:
        res = client.post("/indicators/ai/generate", json={
            "description": "zlema ตัด sma", "model": "m",
        })
        assert res.status_code == 200
        body = res.json()
        assert body["definition"]["name"] == "zl_cross"
        assert body["backtest"] is not None  # มี long/short → quick backtest


def test_generate_repairs_broken_def(db_path: str) -> None:
    broken = {**GOOD_DEF, "lines": {"zl": "import_os()"}}
    ai = FakeAI([json.dumps(broken), json.dumps(GOOD_DEF)])
    with make_client(db_path, ai) as client:
        res = client.post("/indicators/ai/generate", json={
            "description": "x", "model": "m",
        })
        assert res.status_code == 200
        assert len(ai.calls) == 2


def test_generate_refusal_becomes_422(db_path: str) -> None:
    ai = FakeAI([json.dumps({"error": "proprietary indicator - refused"})])
    with make_client(db_path, ai) as client:
        res = client.post("/indicators/ai/generate", json={
            "description": "copy LuxAlgo SMC ให้หน่อย", "model": "m",
        })
        assert res.status_code == 422
        assert "ปฏิเสธ" in res.json()["detail"]


def test_save_list_use_delete_roundtrip(db_path: str) -> None:
    ai = FakeAI([])
    with make_client(db_path, ai) as client:
        # save
        res = client.post("/indicators/defs", json=GOOD_DEF)
        assert res.status_code == 200

        # list
        listed = client.get("/indicators/defs").json()
        assert [d["name"] for d in listed] == ["zl_cross"]

        # ใช้เป็น indicator set ได้เหมือน built-in
        res = client.get("/indicators", params={
            "symbol": "BTC/USDT", "tf": "5m", "set": "zl_cross", "limit": 60,
        })
        assert res.status_code == 200
        lines = res.json()[0]["lines"]
        assert {"zl", "base", "signal_long", "signal_short"} <= set(lines)

        # ใช้เป็น backtest strategy ได้
        res = client.post("/sim/backtest", json={
            "symbol": "BTC/USDT", "tf": "5m", "limit": 200,
            "strategy": "custom:zl_cross",
        })
        assert res.status_code == 200

        # delete
        assert client.delete("/indicators/defs/zl_cross").json() == {"deleted": True}
        assert client.get("/indicators/defs").json() == []
        assert client.delete("/indicators/defs/zl_cross").status_code == 404


def test_unsaved_custom_strategy_404(client: TestClient) -> None:
    res = client.post("/sim/backtest", json={
        "symbol": "BTC/USDT", "tf": "5m", "strategy": "custom:nope",
    })
    assert res.status_code == 404


def test_invalid_def_rejected_on_save(db_path: str) -> None:
    bad = {**GOOD_DEF, "lines": {"zl": "os_system(c)"}}
    with make_client(db_path, FakeAI([])) as client:
        res = client.post("/indicators/defs", json=bad)
        assert res.status_code == 422
