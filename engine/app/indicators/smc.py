"""Smart Money Concepts — first pass: swings, BOS/CHoCH, FVG, Order Blocks.

Source: public SMC/ICT methodology as described in open articles & books
(market structure: break of structure / change of character; fair value gap:
3-candle inefficiency; order block: last opposite candle before an impulse
that breaks structure). Implemented from the written definitions only — no
proprietary Pine code consulted (MEMORY.md #dont-copy-proprietary-pine).
"""

from __future__ import annotations

import pandas as pd

from app.indicators.base import Marker


def swing_points(df: pd.DataFrame, k: int = 2) -> tuple[list[int], list[int]]:
    """Fractal pivots: index i is a swing high if h[i] is the strict max of
    h[i-k..i+k] (mirror for lows). Returns (high_idx, low_idx)."""
    highs: list[int] = []
    lows: list[int] = []
    h, low = df["h"].to_numpy(), df["l"].to_numpy()
    n = len(df)
    for i in range(k, n - k):
        window_h = h[i - k : i + k + 1]
        window_l = low[i - k : i + k + 1]
        if h[i] == window_h.max() and (window_h == h[i]).sum() == 1:
            highs.append(i)
        if low[i] == window_l.min() and (window_l == low[i]).sum() == 1:
            lows.append(i)
    return highs, lows


def structure_markers(df: pd.DataFrame, k: int = 2) -> list[Marker]:
    """BOS/CHoCH from close crossing the latest confirmed swing level.

    - close > last swing high: BOS ถ้า trend เดิมขึ้น, CHoCH ถ้า trend เดิมลง
    - close < last swing low : BOS ถ้า trend เดิมลง, CHoCH ถ้า trend เดิมขึ้น
    trend เริ่มต้น = 0 (unknown) → การ break แรกนับเป็น BOS ของทิศนั้น
    """
    highs, lows = swing_points(df, k)
    ts = df["ts"].to_numpy()
    close = df["c"].to_numpy()
    markers: list[Marker] = []

    hi_iter = iter(highs)
    lo_iter = iter(lows)
    next_hi = next(hi_iter, None)
    next_lo = next(lo_iter, None)
    last_hi_level: float | None = None
    last_lo_level: float | None = None
    trend = 0  # +1 up, -1 down

    for i in range(len(df)):
        # confirm pivots once price is k bars past them
        while next_hi is not None and i >= next_hi + k:
            last_hi_level = float(df["h"].iloc[next_hi])
            next_hi = next(hi_iter, None)
        while next_lo is not None and i >= next_lo + k:
            last_lo_level = float(df["l"].iloc[next_lo])
            next_lo = next(lo_iter, None)

        if last_hi_level is not None and close[i] > last_hi_level:
            kind = "choch_up" if trend == -1 else "bos_up"
            markers.append(Marker(ts=int(ts[i]), kind=kind, price=last_hi_level))
            trend = 1
            last_hi_level = None  # level consumed
        elif last_lo_level is not None and close[i] < last_lo_level:
            kind = "choch_down" if trend == 1 else "bos_down"
            markers.append(Marker(ts=int(ts[i]), kind=kind, price=last_lo_level))
            trend = -1
            last_lo_level = None

    return markers


def fvg_markers(df: pd.DataFrame) -> list[Marker]:
    """3-candle Fair Value Gap:
    bullish: low ของแท่ง i > high ของแท่ง i-2 → gap zone (h[i-2], l[i]) ที่แท่ง i-1
    bearish: high ของแท่ง i < low ของแท่ง i-2 → gap zone (l[i-2], h[i]) ที่แท่ง i-1
    """
    ts = df["ts"].to_numpy()
    h, low = df["h"].to_numpy(), df["l"].to_numpy()
    out: list[Marker] = []
    for i in range(2, len(df)):
        if low[i] > h[i - 2]:
            out.append(Marker(ts=int(ts[i - 1]), kind="fvg_bull",
                              price=float(h[i - 2]), price2=float(low[i])))
        elif h[i] < low[i - 2]:
            out.append(Marker(ts=int(ts[i - 1]), kind="fvg_bear",
                              price=float(h[i]), price2=float(low[i - 2])))
    return out


def order_block_markers(df: pd.DataFrame, k: int = 2) -> list[Marker]:
    """Order Block (basic): แท่งสวนทางแท่งสุดท้ายก่อน move ที่ทำ BOS —
    bullish OB = last down-candle ก่อน bos_up, zone = (l, h) ของแท่งนั้น."""
    structure = structure_markers(df, k)
    ts_to_idx = {int(t): i for i, t in enumerate(df["ts"].to_numpy())}
    o, c = df["o"].to_numpy(), df["c"].to_numpy()
    h, low = df["h"].to_numpy(), df["l"].to_numpy()
    ts = df["ts"].to_numpy()
    out: list[Marker] = []
    for m in structure:
        if m.kind not in ("bos_up", "bos_down", "choch_up", "choch_down"):
            continue
        i = ts_to_idx[m.ts]
        bullish = m.kind.endswith("up")
        for j in range(i - 1, max(i - 20, -1), -1):
            down_candle = c[j] < o[j]
            if down_candle == bullish:  # opposite candle to the break direction
                out.append(Marker(ts=int(ts[j]),
                                  kind="ob_bull" if bullish else "ob_bear",
                                  price=float(low[j]), price2=float(h[j])))
                break
    return out
