import json

import httpx
import pytest
from fastapi.testclient import TestClient

from app.ai.base import AIProvider
from app.ai.ollama import OllamaProvider
from app.api.app import create_app
from app.data.service import DataService

from .fakes import FakeProvider

GOOD_SIGNAL = {
    "side": "long",
    "entry": 105.0,
    "sl": 100.0,
    "tp": [110.0, 115.0],
    "rr": 1.0,
    "confidence": 62,
    "reason": "zlema trend up + bos_up",
    "indicators_used": {"zero_lag": "trend up"},
}


class FakeAI(AIProvider):
    name = "fake-ai"

    def __init__(self, responses: list[str]):
        self.responses = list(responses)
        self.calls: list[list[dict[str, str]]] = []

    async def list_models(self) -> list[str]:
        return ["fake-model:latest"]

    async def complete(self, model: str, messages: list[dict[str, str]],
                       json_mode: bool = False) -> str:
        self.calls.append(messages)
        return self.responses.pop(0)


def make_client(db_path: str, ai: FakeAI) -> TestClient:
    return TestClient(create_app(
        db_path,
        data_service=DataService([FakeProvider()]),
        ai_providers={"ollama": ai},
    ))


def test_analyze_returns_signal_and_persists(db_path: str) -> None:
    ai = FakeAI([json.dumps(GOOD_SIGNAL)])
    with make_client(db_path, ai) as client:
        res = client.post("/analyze", json={
            "symbol": "BTC/USDT", "tfs": ["15m", "60m"], "model": "fake-model:latest",
        })
        assert res.status_code == 200
        sig = res.json()
        assert sig["side"] == "long" and sig["entry"] == 105.0
        assert sig["symbol"] == "BTC/USDT" and sig["tf"] == "15m"
        assert sig["model"] == "fake-model:latest"
        # prompt ต้องมี context ครบ
        user_msg = ai.calls[0][1]["content"]
        assert "BTC/USDT" in user_msg and "15m" in user_msg and "60m" in user_msg
        # persisted
        listed = client.get("/signals", params={"symbol": "BTC/USDT"}).json()
        assert [s["id"] for s in listed] == [sig["id"]]


def test_analyze_repairs_broken_json_once(db_path: str) -> None:
    ai = FakeAI(["not json at all {{", json.dumps(GOOD_SIGNAL)])
    with make_client(db_path, ai) as client:
        res = client.post("/analyze", json={
            "symbol": "BTC/USDT", "tfs": ["15m"], "model": "m",
        })
        assert res.status_code == 200
        assert len(ai.calls) == 2
        assert "invalid" in ai.calls[1][-1]["content"]


def test_analyze_gives_502_when_repair_fails(db_path: str) -> None:
    ai = FakeAI(["broken", "still broken"])
    with make_client(db_path, ai) as client:
        res = client.post("/analyze", json={"symbol": "BTC/USDT", "tfs": ["15m"], "model": "m"})
        assert res.status_code == 502


def test_analyze_no_setup_returns_null(db_path: str) -> None:
    ai = FakeAI([json.dumps({"side": None})])
    with make_client(db_path, ai) as client:
        res = client.post("/analyze", json={"symbol": "BTC/USDT", "tfs": ["15m"], "model": "m"})
        assert res.status_code == 200
        assert res.json() is None
        assert client.get("/signals").json() == []  # ไม่ persist


def test_analyze_unknown_provider_404(db_path: str) -> None:
    ai = FakeAI([])
    with make_client(db_path, ai) as client:
        res = client.post("/analyze", json={
            "symbol": "BTC/USDT", "tfs": ["15m"], "model": "m", "provider": "nope",
        })
        assert res.status_code == 404


def test_ai_models_lists_ready_models(db_path: str) -> None:
    ai = FakeAI([])
    with make_client(db_path, ai) as client:
        res = client.get("/ai/models")
        assert res.json() == {"ollama": [{"id": "fake-model:latest", "recommended": False}]}


@pytest.mark.anyio
async def test_ollama_list_models_parses_tags() -> None:
    def handle(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/tags"
        return httpx.Response(200, json={"models": [{"name": "llama3.1:8b"}]})

    provider = OllamaProvider(client=httpx.AsyncClient(
        transport=httpx.MockTransport(handle), base_url="http://t"))
    assert await provider.list_models() == ["llama3.1:8b"]


@pytest.mark.anyio
async def test_ollama_offline_returns_empty() -> None:
    def handle(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refused")

    provider = OllamaProvider(client=httpx.AsyncClient(
        transport=httpx.MockTransport(handle), base_url="http://t"))
    assert await provider.list_models() == []


@pytest.mark.anyio
async def test_ollama_complete_sends_json_format() -> None:
    def handle(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        assert body["model"] == "llama3.1:8b"
        assert body["format"] == "json"
        assert body["stream"] is False
        return httpx.Response(200, json={"message": {"content": "{\"ok\":1}"}})

    provider = OllamaProvider(client=httpx.AsyncClient(
        transport=httpx.MockTransport(handle), base_url="http://t"))
    out = await provider.complete("llama3.1:8b", [{"role": "user", "content": "hi"}],
                                  json_mode=True)
    assert out == "{\"ok\":1}"
