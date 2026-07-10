import json
import time

from fastapi.testclient import TestClient

from app.api.app import create_app
from app.data.service import DataService

from .fakes import FakeProvider
from .test_ai import GOOD_SIGNAL, FakeAI


def test_backtest_run_completes(client: TestClient) -> None:
    res = client.post("/sim/backtest", json={
        "symbol": "BTC/USDT", "tf": "5m", "limit": 200,
        "config": {"fee_pct": 0, "slippage_pct": 0},
    })
    assert res.status_code == 200
    run_id = res.json()["run_id"]

    run = None
    for _ in range(50):
        run = client.get(f"/sim/runs/{run_id}").json()
        if run["status"] != "running":
            break
        time.sleep(0.1)
    assert run is not None and run["status"] == "done"
    assert run["stats"]["scope"] == "backtest"


def test_sim_run_unknown_404(client: TestClient) -> None:
    assert client.get("/sim/runs/nope").status_code == 404


def test_trades_scope_validation(client: TestClient) -> None:
    assert client.get("/trades", params={"scope": "weird"}).status_code == 422
    assert client.get("/trades").status_code == 200


def test_stats_empty_returns_zeros(client: TestClient) -> None:
    body = client.get("/stats").json()
    assert body["trades"] == 0 and body["scope"] == "all"


def test_analyze_opens_paper_trade_and_streams_updates(db_path: str) -> None:
    """signal จาก /analyze → paper trade เปิดอัตโนมัติ → stream ชน TP → ปิด + WS push."""
    # stream: แท่งแรกไม่ชนอะไร แท่งสองชน TP (110 > 105 entry... GOOD_SIGNAL tp1=110)
    t0 = 1_700_000_100_000 - (1_700_000_100_000 % 300_000)
    from app.models import Candle

    stream = [
        Candle(symbol="BTC/USDT", tf="15m", ts=t0, o=105, h=106, l=104, c=105.5, v=1),
        Candle(symbol="BTC/USDT", tf="15m", ts=t0 + 900_000, o=105.5, h=111, l=105, c=110.5, v=1),
    ]
    provider = FakeProvider(stream_candles=stream)
    ai = FakeAI([json.dumps(GOOD_SIGNAL)])
    app = create_app(db_path, data_service=DataService([provider]), ai_providers={"ollama": ai})

    with TestClient(app) as client:
        with client.websocket_connect("/ws") as ws:
            assert ws.receive_json()["type"] == "engine.hello"
            res = client.post("/analyze", json={
                "symbol": "BTC/USDT", "tfs": ["15m"], "model": "m",
            })
            assert res.status_code == 200

            # ws ต้องเห็น signal.new → trade.update (open) → trade.update (closed win)
            seen: list[dict] = []
            for _ in range(3):
                seen.append(ws.receive_json())
            types = [m["type"] for m in seen]
            assert types[0] == "signal.new"
            assert types[1] == "trade.update" and seen[1]["payload"]["status"] == "open"
            assert types[2] == "trade.update"
            closed = seen[2]["payload"]
            assert closed["status"] == "win"
            assert closed["exit"] is not None

        # persisted แล้ว query ได้ผ่าน /trades + /stats
        trades = client.get("/trades", params={"scope": "paper"}).json()
        assert len(trades) == 1 and trades[0]["status"] == "win"
        stats = client.get("/stats", params={"scope": "paper"}).json()
        assert stats["trades"] == 1 and stats["winrate"] == 100.0
