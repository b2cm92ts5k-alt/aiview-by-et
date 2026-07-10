"""Cloud AI providers (TDD.md §6, F7) — key-gated: instance ถูกสร้างเมื่อมี key
เท่านั้น (key ส่งมาจาก Electron main แบบ in-memory ต่อ session, TDD §9 —
ห้าม log / ห้ามเขียนลงดิสก์).

ทุก provider คืน [] จาก list_models เมื่อ key ใช้ไม่ได้ (401/เน็ตล่ม) —
renderer จึงโชว์ model เฉพาะเมื่อ key valid ตาม F7.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import httpx

from app.ai.base import AIProvider

TIMEOUT = 60.0


class OpenAICompatProvider(AIProvider):
    """OpenAI-compatible chat API — ใช้กับ OpenAI / OpenRouter / GitHub Models."""

    name = "openai"
    base_url = "https://api.openai.com/v1"
    models_url: str | None = None  # override เมื่อ catalog อยู่คนละ host

    def __init__(self, api_key: str, client: httpx.AsyncClient | None = None) -> None:
        self._key = api_key
        self._client = client or httpx.AsyncClient(
            base_url=self.base_url,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=TIMEOUT,
        )

    async def list_models(self) -> list[str]:
        try:
            res = await self._client.get(self.models_url or "/models")
            res.raise_for_status()
        except httpx.HTTPError:
            return []
        body = res.json()
        items = body.get("data", body if isinstance(body, list) else [])
        ids = [str(m.get("id") or m.get("name") or "") for m in items if isinstance(m, dict)]
        return sorted(i for i in ids if i)

    async def complete(
        self, model: str, messages: list[dict[str, str]], json_mode: bool = False
    ) -> str:
        payload: dict[str, Any] = {"model": model, "messages": messages}
        if json_mode:
            payload["response_format"] = {"type": "json_object"}
        res = await self._client.post("/chat/completions", json=payload)
        res.raise_for_status()
        return res.json()["choices"][0]["message"]["content"]

    async def close(self) -> None:
        await self._client.aclose()


class OpenRouterProvider(OpenAICompatProvider):
    name = "openrouter"
    base_url = "https://openrouter.ai/api/v1"


class GitHubModelsProvider(OpenAICompatProvider):
    name = "github"
    base_url = "https://models.github.ai/inference"
    models_url = "https://models.github.ai/catalog/models"


class AnthropicProvider(AIProvider):
    name = "anthropic"
    base_url = "https://api.anthropic.com"

    def __init__(self, api_key: str, client: httpx.AsyncClient | None = None) -> None:
        self._client = client or httpx.AsyncClient(
            base_url=self.base_url,
            headers={"x-api-key": api_key, "anthropic-version": "2023-06-01"},
            timeout=TIMEOUT,
        )

    async def list_models(self) -> list[str]:
        try:
            res = await self._client.get("/v1/models")
            res.raise_for_status()
        except httpx.HTTPError:
            return []
        return sorted(m["id"] for m in res.json().get("data", []))

    async def complete(
        self, model: str, messages: list[dict[str, str]], json_mode: bool = False
    ) -> str:
        system = "\n".join(m["content"] for m in messages if m["role"] == "system")
        chat = [m for m in messages if m["role"] != "system"]
        if json_mode:
            system += "\nRespond with a single valid JSON object only."
        payload: dict[str, Any] = {
            "model": model,
            "max_tokens": 2048,
            "messages": chat,
        }
        if system:
            payload["system"] = system
        res = await self._client.post("/v1/messages", json=payload)
        res.raise_for_status()
        return res.json()["content"][0]["text"]

    async def close(self) -> None:
        await self._client.aclose()


class GoogleProvider(AIProvider):
    name = "google"
    base_url = "https://generativelanguage.googleapis.com"

    def __init__(self, api_key: str, client: httpx.AsyncClient | None = None) -> None:
        self._key = api_key
        self._client = client or httpx.AsyncClient(base_url=self.base_url, timeout=TIMEOUT)

    async def list_models(self) -> list[str]:
        try:
            res = await self._client.get("/v1beta/models", params={"key": self._key})
            res.raise_for_status()
        except httpx.HTTPError:
            return []
        names = [m.get("name", "") for m in res.json().get("models", [])]
        return sorted(n.removeprefix("models/") for n in names if n)

    async def complete(
        self, model: str, messages: list[dict[str, str]], json_mode: bool = False
    ) -> str:
        system = "\n".join(m["content"] for m in messages if m["role"] == "system")
        contents = [
            {"role": "model" if m["role"] == "assistant" else "user",
             "parts": [{"text": m["content"]}]}
            for m in messages if m["role"] != "system"
        ]
        payload: dict[str, Any] = {"contents": contents}
        if system:
            payload["systemInstruction"] = {"parts": [{"text": system}]}
        if json_mode:
            payload["generationConfig"] = {"responseMimeType": "application/json"}
        res = await self._client.post(
            f"/v1beta/models/{model}:generateContent", params={"key": self._key}, json=payload
        )
        res.raise_for_status()
        return res.json()["candidates"][0]["content"]["parts"][0]["text"]

    async def close(self) -> None:
        await self._client.aclose()


# factory รับ api_key → provider (typing เป็น Callable เพราะ ABC ไม่ fix __init__ signature)
CLOUD_PROVIDERS: dict[str, Callable[[str], AIProvider]] = {
    "anthropic": AnthropicProvider,
    "openai": OpenAICompatProvider,
    "google": GoogleProvider,
    "openrouter": OpenRouterProvider,
    "github": GitHubModelsProvider,
}
