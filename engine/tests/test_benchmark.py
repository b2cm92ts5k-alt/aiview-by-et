import json
import time

from fastapi.testclient import TestClient

from app.api.app import create_app
from app.data.service import DataService

from .fakes import FakeProvider
from .test_ai import GOOD_SIGNAL, FakeAI


def make_client(db_path: str, ai_providers) -> TestClient:
    return TestClient(create_app(
        db_path,
        data_service=DataService([FakeProvider()]),
        ai_providers=ai_providers,
    ))


def poll_run(client: TestClient, run_id: str) -> dict:
    for _ in range(100):
        run = client.get(f"/benchmark/runs/{run_id}").json()
        if run["status"] != "running":
            return run
        time.sleep(0.05)
    raise TimeoutError("benchmark run stuck")


def test_benchmark_compares_two_models(db_path: str) -> None:
    # model A: ให้ signal ทุก window (3) · model B: no-setup ทุก window
    windows = 3
    ai_a = FakeAI([json.dumps(GOOD_SIGNAL)] * windows)
    ai_b = FakeAI([json.dumps({"side": None})] * windows)
    with make_client(db_path, {"prov_a": ai_a, "prov_b": ai_b}) as client:
        res = client.post("/benchmark", json={
            "models": [
                {"provider": "prov_a", "model": "model-a"},
                {"provider": "prov_b", "model": "model-b"},
            ],
            "symbol": "BTC/USDT", "tf": "5m", "limit": 400, "windows": windows,
        })
        assert res.status_code == 200
        run = poll_run(client, res.json()["run_id"])
        assert run["status"] == "done", run
        a, b = run["results"]
        assert a["model"] == "model-a"
        assert a["signals"] == windows and a["no_setup"] == 0
        assert b["signals"] == 0 and b["no_setup"] == windows
        assert a["stats"]["trades"] >= 0
        # ทุก model เห็นข้อมูลชุดเดียวกัน → เทียบกันได้
        assert a["stats"]["scope"] == "benchmark:prov_a:model-a"


def test_benchmark_unknown_provider_404(db_path: str) -> None:
    with make_client(db_path, {"ollama": FakeAI([])}) as client:
        res = client.post("/benchmark", json={
            "models": [{"provider": "nope", "model": "x"}],
        })
        assert res.status_code == 404


def test_benchmark_empty_models_422(db_path: str) -> None:
    with make_client(db_path, {"ollama": FakeAI([])}) as client:
        res = client.post("/benchmark", json={"models": []})
        assert res.status_code == 422


def test_benchmark_model_errors_counted_not_fatal(db_path: str) -> None:
    # ตอบ JSON พังทุกครั้ง (รวม repair) → นับเป็น errors ไม่ล้มทั้ง run
    ai_bad = FakeAI(["broken"] * 10)
    with make_client(db_path, {"prov": ai_bad}) as client:
        res = client.post("/benchmark", json={
            "models": [{"provider": "prov", "model": "bad"}],
            "tf": "5m", "limit": 300, "windows": 2,
        })
        run = poll_run(client, res.json()["run_id"])
        assert run["status"] == "done"
        assert run["results"][0]["errors"] == 2
        assert run["results"][0]["signals"] == 0
