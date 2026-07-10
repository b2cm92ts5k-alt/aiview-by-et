import json

import httpx
import pytest
from fastapi.testclient import TestClient

from app.ai.cloud import (
    AnthropicProvider,
    GoogleProvider,
    OpenAICompatProvider,
    OpenRouterProvider,
)
from app.ai.recommended import is_recommended
from app.api.app import create_app
from app.data.service import DataService

from .fakes import FakeProvider
from .test_ai import FakeAI


def _client(handler, base="https://t") -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.MockTransport(handler), base_url=base)


# ---------- provider adapters (mocked HTTP) ----------


@pytest.mark.anyio
async def test_openai_compat_list_and_complete() -> None:
    def handle(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/models":
            assert request.headers["Authorization"] == "Bearer sk-x"
            return httpx.Response(200, json={"data": [{"id": "gpt-5"}, {"id": "gpt-4o"}]})
        body = json.loads(request.content)
        assert body["response_format"] == {"type": "json_object"}
        return httpx.Response(200, json={
            "choices": [{"message": {"content": "{\"ok\":1}"}}],
        })

    p = OpenAICompatProvider("sk-x", client=_client(handle))
    p._client.headers["Authorization"] = "Bearer sk-x"
    assert await p.list_models() == ["gpt-4o", "gpt-5"]
    out = await p.complete("gpt-5", [{"role": "user", "content": "hi"}], json_mode=True)
    assert out == "{\"ok\":1}"


@pytest.mark.anyio
async def test_anthropic_system_split_and_parse() -> None:
    def handle(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/v1/models":
            return httpx.Response(200, json={"data": [{"id": "claude-sonnet-5"}]})
        body = json.loads(request.content)
        assert "system" in body and "JSON" in body["system"]
        assert all(m["role"] != "system" for m in body["messages"])
        return httpx.Response(200, json={"content": [{"text": "{\"a\":1}"}]})

    p = AnthropicProvider("k", client=_client(handle))
    assert await p.list_models() == ["claude-sonnet-5"]
    out = await p.complete("claude-sonnet-5", [
        {"role": "system", "content": "you are x"},
        {"role": "user", "content": "hi"},
    ], json_mode=True)
    assert out == "{\"a\":1}"


@pytest.mark.anyio
async def test_google_contents_mapping() -> None:
    def handle(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/v1beta/models":
            return httpx.Response(200, json={
                "models": [{"name": "models/gemini-3-pro"}, {"name": "models/gemini-flash"}],
            })
        body = json.loads(request.content)
        assert body["generationConfig"]["responseMimeType"] == "application/json"
        roles = [c["role"] for c in body["contents"]]
        assert roles == ["user", "model", "user"]
        return httpx.Response(200, json={
            "candidates": [{"content": {"parts": [{"text": "{}"}]}}],
        })

    p = GoogleProvider("k", client=_client(handle))
    assert await p.list_models() == ["gemini-3-pro", "gemini-flash"]
    out = await p.complete("gemini-3-pro", [
        {"role": "system", "content": "sys"},
        {"role": "user", "content": "a"},
        {"role": "assistant", "content": "b"},
        {"role": "user", "content": "c"},
    ], json_mode=True)
    assert out == "{}"


@pytest.mark.anyio
async def test_invalid_key_returns_empty_models() -> None:
    def handle(_: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"error": "invalid key"})

    p = OpenRouterProvider("bad", client=_client(handle))
    assert await p.list_models() == []  # key-gate F7: ไม่ valid = ไม่โชว์ model


# ---------- recommended tags (จาก AI_MODELS.md ที่เคาะแล้ว) ----------


@pytest.mark.parametrize("provider,model,expected", [
    ("anthropic", "claude-opus-4-8", True),
    ("anthropic", "claude-sonnet-5", True),
    ("anthropic", "claude-haiku-4-5", False),
    ("openai", "gpt-5", True),
    ("openai", "gpt-5-mini", False),
    ("openai", "o3-pro", True),
    ("google", "gemini-3-pro", True),
    ("google", "gemini-flash", False),
    ("ollama", "qwen3:14b", True),
    ("ollama", "qwen2.5:32b-instruct", True),
    ("ollama", "qwen3:8b", False),
    ("ollama", "deepseek-r1:14b", True),
    ("ollama", "llama3.1:8b", False),
    ("openrouter", "anything", False),
])
def test_recommended_tags(provider: str, model: str, expected: bool) -> None:
    assert is_recommended(provider, model) is expected


# ---------- key handoff endpoint ----------


def test_set_key_registers_provider_and_lists(db_path: str) -> None:
    app = create_app(db_path, data_service=DataService([FakeProvider()]),
                     ai_providers={"ollama": FakeAI([])})
    with TestClient(app) as client:
        status = client.get("/providers/keys").json()
        assert status["ai"] == ["ollama"]
        assert "anthropic" in status["cloud_available"]

        res = client.post("/providers/keys", json={"provider": "anthropic", "key": "sk-a"})
        assert res.status_code == 200
        assert "anthropic" in client.get("/providers/keys").json()["ai"]

        # remove
        assert client.delete("/providers/keys/anthropic").status_code == 200
        assert "anthropic" not in client.get("/providers/keys").json()["ai"]


def test_set_key_unknown_provider_404(db_path: str) -> None:
    app = create_app(db_path, data_service=DataService([FakeProvider()]),
                     ai_providers={"ollama": FakeAI([])})
    with TestClient(app) as client:
        res = client.post("/providers/keys", json={"provider": "nope", "key": "x"})
        assert res.status_code == 404


def test_set_key_twelvedata_adds_data_provider(db_path: str) -> None:
    app = create_app(db_path, data_service=DataService([FakeProvider()]),
                     ai_providers={"ollama": FakeAI([])})
    with TestClient(app) as client:
        before = client.get("/markets").json()
        assert all(s["provider"] != "twelvedata" for s in before["symbols"])
        res = client.post("/providers/keys", json={"provider": "twelvedata", "key": "td-k"})
        assert res.status_code == 200
        after = client.get("/markets").json()
        assert any(s["provider"] == "twelvedata" for s in after["symbols"])
        assert "gold" in after["asset_classes"]
