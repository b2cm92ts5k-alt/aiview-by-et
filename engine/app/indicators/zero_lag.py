"""Zero-Lag EMA — public formula.

Source: John Ehlers & Ric Way, "Zero Lag (Well, Almost)" (2010, public paper);
also the widely documented ZLEMA form: EMA of de-lagged price
    lag = (period - 1) // 2
    zlema = EMA(2*price - price.shift(lag), period)
Implemented from the published formula only — NOT ported from any proprietary
Pine indicator (MEMORY.md #dont-copy-proprietary-pine).
"""

from __future__ import annotations

import pandas as pd

from app.indicators.basic import ema


def zlema(series: pd.Series, period: int = 21) -> pd.Series:
    lag = (period - 1) // 2
    dedlagged = 2 * series - series.shift(lag)
    return ema(dedlagged, period)


def zlema_trend(close: pd.Series, period: int = 21) -> pd.Series:
    """+1 when close above rising ZLEMA, -1 when below falling, else 0."""
    z = zlema(close, period)
    rising = z.diff() > 0
    up = (close > z) & rising
    down = (close < z) & ~rising
    return up.astype(int) - down.astype(int)
