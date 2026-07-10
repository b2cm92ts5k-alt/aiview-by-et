"""Rule-based signal generator for backtests (deterministic, no LLM).

"zlema-smc": long เมื่อ zlema trend พลิกเป็น +1 และมี bos_up/choch_up ล่าสุด
(short = กลับด้าน). SL = swing ฝั่งตรงข้ามล่าสุด (fallback: ATR×1.5),
TP1/TP2 = RR 1.5 / 2.5 จากระยะ SL.

ใช้ indicator ชุดเดียวกับที่ AI เห็น (app/indicators) — เป็น proxy เชิงกติกา
ของ setup ที่ prompt สอน AI ให้มอง เพื่อให้ backtest ได้เร็วโดยไม่ยิง LLM รายแท่ง.
"""

from __future__ import annotations

import uuid

import pandas as pd

from app.indicators.base import candles_to_df
from app.indicators.basic import atr
from app.indicators.smc import structure_markers, swing_points
from app.indicators.zero_lag import zlema_trend
from app.models import Candle, Signal

RR_TP = (1.5, 2.5)
ATR_SL_MULT = 1.5
WARMUP_BARS = 50  # ให้ indicator นิ่งก่อนเริ่มออก signal


def generate_signals(candles: list[Candle], strategy: str = "zlema-smc") -> list[Signal]:
    if strategy != "zlema-smc":
        raise ValueError(f"unknown strategy: {strategy}")
    if len(candles) <= WARMUP_BARS:
        return []

    df = candles_to_df(candles)
    trend = zlema_trend(df["c"], 21)
    atr14 = atr(df["h"], df["l"], df["c"], 14)
    marks = structure_markers(df)
    highs_idx, lows_idx = swing_points(df)
    ts_arr = df["ts"].to_numpy()

    # โครงสร้างล่าสุด ณ ts ใดๆ (bos/choch direction)
    mark_by_ts: dict[int, str] = {m.ts: m.kind for m in marks}

    signals: list[Signal] = []
    last_structure: str | None = None
    swing_lo_iter = [int(i) for i in lows_idx]
    swing_hi_iter = [int(i) for i in highs_idx]

    for i in range(WARMUP_BARS, len(df)):
        ts = int(ts_arr[i])
        if ts in mark_by_ts:
            last_structure = mark_by_ts[ts]

        flipped_up = trend.iloc[i] == 1 and trend.iloc[i - 1] != 1
        flipped_down = trend.iloc[i] == -1 and trend.iloc[i - 1] != -1
        if not (flipped_up or flipped_down):
            continue

        close = float(df["c"].iloc[i])
        a = float(atr14.iloc[i]) if not pd.isna(atr14.iloc[i]) else 0.0

        if flipped_up and last_structure in ("bos_up", "choch_up"):
            side = "long"
            recent_lows = [j for j in swing_lo_iter if j < i]
            sl = float(df["l"].iloc[recent_lows[-1]]) if recent_lows else close - a * ATR_SL_MULT
            if sl >= close:
                sl = close - a * ATR_SL_MULT
        elif flipped_down and last_structure in ("bos_down", "choch_down"):
            side = "short"
            recent_highs = [j for j in swing_hi_iter if j < i]
            sl = float(df["h"].iloc[recent_highs[-1]]) if recent_highs else close + a * ATR_SL_MULT
            if sl <= close:
                sl = close + a * ATR_SL_MULT
        else:
            continue

        risk = abs(close - sl)
        if risk <= 0:
            continue
        direction = 1 if side == "long" else -1
        tp = [close + direction * risk * rr for rr in RR_TP]

        signals.append(Signal(
            id=str(uuid.uuid4()),
            symbol=candles[0].symbol,
            tf=candles[0].tf,
            side=side,  # type: ignore[arg-type]
            entry=close,
            sl=sl,
            tp=tp,
            rr=RR_TP[0],
            confidence=0,  # rule-based ไม่มี confidence
            reason=f"zlema flip {side} + {last_structure}",
            indicators_used={"zero_lag": "trend flip", "smc": last_structure or ""},
            model=f"rule:{strategy}",
            created_at=ts,
        ))
    return signals


def bar_index_of(candles: list[Candle], ts: int) -> int:
    for i, c in enumerate(candles):
        if c.ts == ts:
            return i
    raise ValueError(f"ts {ts} not in candles")
