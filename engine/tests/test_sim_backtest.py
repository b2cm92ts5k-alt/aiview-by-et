"""Backtest on crafted candles: trend flip + structure → signal → trade closes."""

from app.models import Candle, Signal, SimConfig
from app.sim.backtest import RunRegistry, run_backtest
from app.sim.strategy import generate_signals

CFG = SimConfig(initial_capital=10_000, risk_per_trade_pct=1.0,
                fee_pct=0.0, slippage_pct=0.0, timeout_bars=20)


def make_wave(n: int = 120) -> list[Candle]:
    """ลงแบบ zigzag แล้วพลิกขึ้นแรง — มี swing highs/lows ให้ BOS + zlema flip."""
    import math

    candles = []
    for i in range(n):
        base = 200.0 - i * 1.0 if i < 60 else 140.0 + (i - 60) * 2.5
        price = base + 4.0 * math.sin(i * 0.7)  # oscillation สร้าง local extremes
        o = price
        c = price + (1.0 if i >= 60 else -0.4)
        h = max(o, c) + 1
        low = min(o, c) - 1
        candles.append(Candle(symbol="BTC/USDT", tf="15m", ts=1_000_000 + i * 900_000,
                              o=o, h=h, l=low, c=c, v=10))
    return candles


def test_replay_mode_closes_trades() -> None:
    candles = make_wave()
    # signal มือ: long ที่แท่ง 70 entry=close, SL ต่ำกว่า, TP ใกล้ๆ ให้ชนแน่
    entry_bar = candles[70]
    sig = Signal(id="s1", symbol="BTC/USDT", tf="15m", side="long",
                 entry=entry_bar.c, sl=entry_bar.c - 5, tp=[entry_bar.c + 3],
                 rr=0.6, confidence=50, reason="", model="manual",
                 created_at=entry_bar.ts)
    trades, stats = run_backtest(candles, CFG, signals=[sig])
    assert len(trades) == 1
    assert trades[0].status == "win"
    assert stats.trades == 1 and stats.winrate == 100.0


def test_rule_strategy_generates_signals_on_wave() -> None:
    candles = make_wave()
    signals = generate_signals(candles)
    assert len(signals) >= 1
    s = signals[0]
    assert s.side in ("long", "short")
    assert s.model == "rule:zlema-smc"
    assert abs(s.entry - s.sl) > 0
    # TP เรียงตามทิศ
    direction = 1 if s.side == "long" else -1
    assert (s.tp[0] - s.entry) * direction > 0


def test_full_backtest_on_wave_produces_stats() -> None:
    candles = make_wave()
    trades, stats = run_backtest(candles, CFG)
    assert stats.scope == "backtest"
    # ทุก trade ต้องผูก signal + มีสถานะ
    for t in trades:
        assert t.status in ("open", "win", "loss", "be", "timeout")
        assert t.model == "rule:zlema-smc"


def test_run_registry_lifecycle() -> None:
    reg = RunRegistry()
    run_id = reg.create()
    assert reg.get(run_id) is not None
    assert reg.get(run_id).status == "running"  # type: ignore[union-attr]
    reg.fail(run_id, "boom")
    assert reg.get(run_id).status == "error"  # type: ignore[union-attr]
    assert reg.get("nope") is None
