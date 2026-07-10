"""DataProvider interface (TDD.md §4 / ARCHITECTURE.md §7)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator

from pydantic import BaseModel

from app.models import Candle, SymbolInfo, Timeframe


class Capabilities(BaseModel):
    timeframes: list[Timeframe]  # tfs the provider serves natively
    realtime: bool  # true = push (WS), false = engine polls


class DataProvider(ABC):
    name: str

    @abstractmethod
    def capabilities(self) -> Capabilities: ...

    @abstractmethod
    async def list_symbols(self) -> list[SymbolInfo]: ...

    @abstractmethod
    async def fetch_ohlcv(
        self,
        symbol: str,
        tf: Timeframe,
        since: int | None = None,
        limit: int = 500,
    ) -> list[Candle]:
        """History, oldest→newest, normalized to the central Candle schema."""

    @abstractmethod
    def subscribe(self, symbol: str, tf: Timeframe) -> AsyncIterator[Candle]:
        """Yield the forming candle on every update until cancelled."""

    async def close(self) -> None:  # noqa: B027 — optional cleanup hook
        pass
