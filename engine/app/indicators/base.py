"""Indicator interface (ARCHITECTURE.md §7, TDD.md §5).

⚠️ Every indicator implementation must derive from a PUBLIC methodology and
cite its source in the module docstring — never port proprietary Pine Script
(MEMORY.md #dont-copy-proprietary-pine).
"""

from __future__ import annotations

from abc import ABC, abstractmethod

import pandas as pd
from pydantic import BaseModel

from app.models import Candle


class Marker(BaseModel):
    ts: int
    kind: str  # e.g. "bos_up", "choch_down", "fvg_bull", "ob_bear", "swing_high"
    price: float
    price2: float | None = None  # zone indicators (FVG/OB) span price..price2
    label: str | None = None


class IndicatorResult(BaseModel):
    name: str
    # line name -> aligned values (None where undefined); ts axis = input candles
    lines: dict[str, list[float | None]] = {}
    markers: list[Marker] = []


class Indicator(ABC):
    name: str

    @abstractmethod
    def compute(self, df: pd.DataFrame) -> IndicatorResult:
        """df columns: ts, o, h, l, c, v (oldest→newest)."""


def candles_to_df(candles: list[Candle]) -> pd.DataFrame:
    return pd.DataFrame([c.model_dump() for c in candles], columns=["ts", "o", "h", "l", "c", "v"])
