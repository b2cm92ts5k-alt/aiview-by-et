"""AIProvider interface (TDD.md §6): list_models + complete.

Cloud providers are key-gated (F7) — a provider with no key must not be
registered, so /ai/models naturally returns only usable models.
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class AIProvider(ABC):
    name: str

    @abstractmethod
    async def list_models(self) -> list[str]:
        """Models ready to use right now (pulled locally / key valid)."""

    @abstractmethod
    async def complete(
        self, model: str, messages: list[dict[str, str]], json_mode: bool = False
    ) -> str:
        """messages = [{role, content}]; returns assistant text."""

    async def close(self) -> None:  # noqa: B027
        pass
