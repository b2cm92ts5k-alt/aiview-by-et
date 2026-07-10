"""Fill model (TDD.md §7 + spec.md Decisions 2026-07-10):

- entry ที่ราคา signal (+slippage ตามทิศ)
- exit เต็มไม้ที่ TP1 / SL / timeout
- แท่งเดียวกันแตะทั้ง SL และ TP → นับ SL ก่อน (conservative)
- sizing = risk% ของทุนตั้งต้น (non-compounding): qty = risk_amount / |entry - sl|
- fee + slippage คิดต่อขา (เข้า/ออก) เป็น % ของ notional
"""

from __future__ import annotations

import time
import uuid

from app.models import Candle, Signal, SimConfig, Trade

BE_EPSILON_R = 0.05  # |R| < ค่านี้ถือว่า break-even


def open_trade(signal: Signal, config: SimConfig, opened_at: int | None = None) -> Trade:
    if signal.entry <= 0 or signal.sl <= 0 or not signal.tp:
        raise ValueError("signal missing entry/sl/tp")
    risk_dist = abs(signal.entry - signal.sl)
    if risk_dist == 0:
        raise ValueError("entry == sl")
    slip = signal.entry * config.slippage_pct / 100
    entry = signal.entry + slip if signal.side == "long" else signal.entry - slip
    risk_amount = config.initial_capital * config.risk_per_trade_pct / 100
    qty = risk_amount / risk_dist
    return Trade(
        id=str(uuid.uuid4()),
        signal_id=signal.id,
        symbol=signal.symbol,
        tf=signal.tf,
        side=signal.side,
        entry=entry,
        sl=signal.sl,
        tp=signal.tp[0],
        qty=qty,
        model=signal.model,
        opened_at=opened_at if opened_at is not None else int(time.time() * 1000),
    )


def check_exit(trade: Trade, candle: Candle, bars_open: int, config: SimConfig
               ) -> tuple[float, str] | None:
    """คืน (exit_price, kind) เมื่อไม้ควรปิดในแท่งนี้ — kind: sl|tp|timeout."""
    if trade.side == "long":
        hit_sl = candle.l <= trade.sl
        hit_tp = candle.h >= trade.tp
    else:
        hit_sl = candle.h >= trade.sl
        hit_tp = candle.l <= trade.tp
    if hit_sl:  # SL ก่อนเสมอเมื่อชนทั้งคู่ (conservative)
        return trade.sl, "sl"
    if hit_tp:
        return trade.tp, "tp"
    if bars_open >= config.timeout_bars:
        return candle.c, "timeout"
    return None


def close_trade(trade: Trade, exit_price: float, kind: str, closed_at: int,
                config: SimConfig) -> Trade:
    slip = exit_price * config.slippage_pct / 100
    exit_eff = exit_price - slip if trade.side == "long" else exit_price + slip
    direction = 1 if trade.side == "long" else -1
    gross = (exit_eff - trade.entry) * direction * trade.qty
    fees = (trade.entry + exit_eff) * trade.qty * config.fee_pct / 100
    pnl = gross - fees
    risk_amount = abs(trade.entry - trade.sl) * trade.qty
    r_multiple = pnl / risk_amount if risk_amount else 0.0

    if kind == "timeout":
        status = "timeout" if abs(r_multiple) >= BE_EPSILON_R else "be"
    elif abs(r_multiple) < BE_EPSILON_R:
        status = "be"
    else:
        status = "win" if pnl > 0 else "loss"

    return trade.model_copy(update={
        "exit": exit_eff,
        "pnl": round(pnl, 8),
        "r_multiple": round(r_multiple, 4),
        "status": status,
        "closed_at": closed_at,
    })
