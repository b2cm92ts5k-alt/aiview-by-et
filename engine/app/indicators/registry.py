"""Indicator set registry — 'core' = ชุดเริ่มต้นตาม TDD.md §5."""

from __future__ import annotations

import math

import pandas as pd

from app.indicators import smc
from app.indicators.base import IndicatorResult
from app.indicators.basic import atr, ema, macd, rsi
from app.indicators.zero_lag import zlema, zlema_trend


def _line(series: pd.Series) -> list[float | None]:
    return [None if (v is None or (isinstance(v, float) and math.isnan(v))) else float(v)
            for v in series.tolist()]


def compute_core(df: pd.DataFrame) -> list[IndicatorResult]:
    close, high, low = df["c"], df["h"], df["l"]
    macd_line, macd_sig, macd_hist = macd(close)
    return [
        IndicatorResult(name="ema", lines={"ema20": _line(ema(close, 20)),
                                           "ema50": _line(ema(close, 50))}),
        IndicatorResult(name="rsi", lines={"rsi14": _line(rsi(close, 14))}),
        IndicatorResult(name="atr", lines={"atr14": _line(atr(high, low, close, 14))}),
        IndicatorResult(name="macd", lines={"macd": _line(macd_line),
                                            "signal": _line(macd_sig),
                                            "hist": _line(macd_hist)}),
        IndicatorResult(name="zero_lag", lines={"zlema21": _line(zlema(close, 21)),
                                                "trend": _line(zlema_trend(close, 21))}),
        IndicatorResult(name="smc", markers=(smc.structure_markers(df)
                                             + smc.fvg_markers(df)
                                             + smc.order_block_markers(df))),
    ]


SETS = {"core": compute_core}
