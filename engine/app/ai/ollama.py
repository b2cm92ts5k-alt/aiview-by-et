"""Ollama local provider — HTTP API on localhost:11434 (TDD.md §1, §6)."""

from __future__ import annotations

import httpx

from app.ai.base import AIProvider

DEFAULT_BASE_URL = "http://127.0.0.1:11434"


class OllamaProvider(AIProvider):
    name = "ollama"

    def __init__(self, base_url: str = DEFAULT_BASE_URL,
                 client: httpx.AsyncClient | None = None) -> None:
        self._client = client or httpx.AsyncClient(base_url=base_url, timeout=120.0)

    async def list_models(self) -> list[str]:
        try:
            res = await self._client.get("/api/tags")
            res.raise_for_status()
        except httpx.HTTPError:
            return []  # Ollama ไม่ได้รัน = ไม่มี local model ให้ใช้ (key-gate เทียบเท่า F7)
        return [m["name"] for m in res.json().get("models", [])]

    async def complete(
        self, model: str, messages: list[dict[str, str]], json_mode: bool = False
    ) -> str:
        body: dict = {"model": model, "messages": messages, "stream": False}
        if json_mode:
            body["format"] = "json"
        res = await self._client.post("/api/chat", json=body)
        res.raise_for_status()
        return res.json()["message"]["content"]

    async def close(self) -> None:
        await self._client.aclose()
