"""Baseline indicators — all from public, textbook formulas:

- SMA/EMA: standard moving averages (any TA textbook)
- RSI: J. Welles Wilder, "New Concepts in Technical Trading Systems" (1978)
- MACD: Gerald Appel (1970s), 12/26/9 convention
- ATR: Wilder (1978), RMA smoothing
"""

from __future__ import annotations

import pandas as pd


def sma(series: pd.Series, period: int) -> pd.Series:
    return series.rolling(period).mean()


def ema(series: pd.Series, period: int) -> pd.Series:
    # standard EMA, alpha = 2/(period+1), seeded per pandas adjust=False recurrence
    return series.ewm(span=period, adjust=False).mean()


def rma(series: pd.Series, period: int) -> pd.Series:
    # Wilder's smoothing (RMA), alpha = 1/period
    return series.ewm(alpha=1 / period, adjust=False).mean()


def rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0.0)
    loss = (-delta).clip(lower=0.0)
    avg_gain = rma(gain, period)
    avg_loss = rma(loss, period)
    rs = avg_gain / avg_loss
    out = 100 - (100 / (1 + rs))
    return out.where(avg_loss != 0, 100.0).mask(close.diff().isna())


def macd(
    close: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9
) -> tuple[pd.Series, pd.Series, pd.Series]:
    line = ema(close, fast) - ema(close, slow)
    sig = ema(line, signal)
    return line, sig, line - sig


def true_range(h: pd.Series, low: pd.Series, c: pd.Series) -> pd.Series:
    prev_close = c.shift(1)
    return pd.concat(
        [h - low, (h - prev_close).abs(), (low - prev_close).abs()], axis=1
    ).max(axis=1)


def atr(h: pd.Series, low: pd.Series, c: pd.Series, period: int = 14) -> pd.Series:
    return rma(true_range(h, low, c), period)
