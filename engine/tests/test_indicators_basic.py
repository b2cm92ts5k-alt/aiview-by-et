"""Indicator correctness vs hand-computed reference values (TDD §5, §10)."""

import pandas as pd
import pytest

from app.indicators.basic import atr, ema, macd, rma, rsi, sma
from app.indicators.zero_lag import zlema


def s(*vals: float) -> pd.Series:
    return pd.Series(list(vals), dtype=float)


def test_sma_hand_computed() -> None:
    out = sma(s(1, 2, 3, 4, 5), 3)
    assert pd.isna(out.iloc[0]) and pd.isna(out.iloc[1])
    assert out.iloc[2] == pytest.approx(2.0)
    assert out.iloc[4] == pytest.approx(4.0)


def test_ema_hand_computed() -> None:
    # EMA(3), alpha=0.5, seed = first value (pandas adjust=False):
    # 1 → 1.5 → 2.25 → 3.125 → 4.0625
    out = ema(s(1, 2, 3, 4, 5), 3)
    assert out.iloc[0] == pytest.approx(1.0)
    assert out.iloc[1] == pytest.approx(1.5)
    assert out.iloc[4] == pytest.approx(4.0625)


def test_rma_wilder_smoothing() -> None:
    # RMA(2), alpha=0.5 — same recurrence as EMA(3) here
    out = rma(s(2, 4, 6), 2)
    assert out.iloc[1] == pytest.approx(3.0)
    assert out.iloc[2] == pytest.approx(4.5)


def test_rsi_all_gains_is_100() -> None:
    out = rsi(s(*range(1, 20)), 14)
    assert out.iloc[-1] == pytest.approx(100.0)


def test_rsi_hand_computed_period_2() -> None:
    # closes 1,2,3,2 · RMA(alpha=.5) seeds ที่ค่า non-NaN แรก (idx1):
    # gains 1,1,0 → avg_gain: 1, 1, 0.5 · losses 0,0,1 → avg_loss: 0, 0, 0.5
    # RSI@3 = 100 - 100/(1 + 0.5/0.5) = 50
    out = rsi(s(1, 2, 3, 2), 2)
    assert out.iloc[3] == pytest.approx(50.0)
    assert out.iloc[2] == pytest.approx(100.0)  # ยังไม่มี loss → 100


def test_macd_is_ema_diff() -> None:
    close = s(*[float(x) for x in range(1, 40)])
    line, sig, hist = macd(close)
    expect = ema(close, 12) - ema(close, 26)
    assert line.iloc[-1] == pytest.approx(expect.iloc[-1])
    assert hist.iloc[-1] == pytest.approx(line.iloc[-1] - sig.iloc[-1])


def test_atr_hand_computed() -> None:
    # bars (h,l,c): (12,10,11), (13,11,12), (15,12,14)
    # TR: 2, 2, 3 → RMA(2): 2 → 2 → 2.5
    h, low, c = s(12, 13, 15), s(10, 11, 12), s(11, 12, 14)
    out = atr(h, low, c, 2)
    assert out.iloc[2] == pytest.approx(2.5)


def test_zlema_formula() -> None:
    # period 5 → lag 2 → zlema = EMA(2*p - p.shift(2), 5)
    close = s(*[float(x) for x in range(1, 15)])
    expected = ema(2 * close - close.shift(2), 5)
    out = zlema(close, 5)
    pd.testing.assert_series_equal(out, expected)


def test_zlema_leads_ema_on_trend() -> None:
    close = s(*[float(x) for x in range(1, 30)])
    assert zlema(close, 9).iloc[-1] > ema(close, 9).iloc[-1]
