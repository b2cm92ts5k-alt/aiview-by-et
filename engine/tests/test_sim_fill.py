import pytest

from app.models import Candle, Signal, SimConfig
from app.sim import fill

CFG_CLEAN = SimConfig(initial_capital=10_000, risk_per_trade_pct=1.0,
                      fee_pct=0.0, slippage_pct=0.0, timeout_bars=5)


def sig(side: str = "long", entry: float = 100.0, sl: float = 95.0,
        tp: list[float] | None = None) -> Signal:
    return Signal(id="s1", symbol="BTC/USDT", tf="15m", side=side,  # type: ignore[arg-type]
                  entry=entry, sl=sl, tp=tp or [110.0], rr=2.0, confidence=50,
                  reason="", model="test", created_at=1000)


def candle(h: float, low: float, c: float, ts: int = 2000) -> Candle:
    return Candle(symbol="BTC/USDT", tf="15m", ts=ts, o=c, h=h, l=low, c=c, v=1)


def test_open_trade_risk_sizing() -> None:
    # risk 1% ของ 10000 = 100 · ระยะ SL = 5 → qty = 20
    t = fill.open_trade(sig(), CFG_CLEAN, opened_at=1000)
    assert t.qty == pytest.approx(20.0)
    assert t.entry == pytest.approx(100.0)
    assert t.tp == 110.0 and t.sl == 95.0


def test_win_pnl_hand_computed() -> None:
    t = fill.open_trade(sig(), CFG_CLEAN, opened_at=1000)
    closed = fill.close_trade(t, 110.0, "tp", 3000, CFG_CLEAN)
    # (110-100)*20 = 200 · R = 200/100 = 2
    assert closed.pnl == pytest.approx(200.0)
    assert closed.r_multiple == pytest.approx(2.0)
    assert closed.status == "win"


def test_loss_with_fee_and_slippage() -> None:
    cfg = SimConfig(initial_capital=10_000, risk_per_trade_pct=1.0,
                    fee_pct=0.1, slippage_pct=0.1, timeout_bars=5)
    t = fill.open_trade(sig(), cfg, opened_at=1000)
    # slippage เข้า: 100*1.001 = 100.1 · qty = 100/5 = 20
    assert t.entry == pytest.approx(100.1)
    closed = fill.close_trade(t, 95.0, "sl", 3000, cfg)
    # exit eff = 95*(1-0.001) = 94.905 · gross = (94.905-100.1)*20 = -103.9
    # fees = (100.1+94.905)*20*0.001 = 3.9001 → pnl = -107.8001
    assert closed.pnl == pytest.approx(-107.8001)
    assert closed.status == "loss"


def test_short_side_pnl() -> None:
    t = fill.open_trade(sig(side="short", entry=100, sl=105, tp=[90.0]), CFG_CLEAN, 1000)
    closed = fill.close_trade(t, 90.0, "tp", 3000, CFG_CLEAN)
    # qty = 100/5 = 20 · (100-90)*20 = 200
    assert closed.pnl == pytest.approx(200.0)
    assert closed.status == "win"


def test_sl_first_when_candle_hits_both() -> None:
    t = fill.open_trade(sig(), CFG_CLEAN, 1000)
    # แท่งกว้าง: low 94 (ชน SL 95) + high 111 (ชน TP 110) → SL ก่อน
    exit_info = fill.check_exit(t, candle(h=111, low=94, c=100), bars_open=1, config=CFG_CLEAN)
    assert exit_info == (95.0, "sl")


def test_tp_hit_long() -> None:
    t = fill.open_trade(sig(), CFG_CLEAN, 1000)
    assert fill.check_exit(t, candle(h=110.5, low=99, c=110), 1, CFG_CLEAN) == (110.0, "tp")


def test_no_exit_inside_range() -> None:
    t = fill.open_trade(sig(), CFG_CLEAN, 1000)
    assert fill.check_exit(t, candle(h=105, low=96, c=100), 1, CFG_CLEAN) is None


def test_timeout_closes_at_close_price() -> None:
    t = fill.open_trade(sig(), CFG_CLEAN, 1000)
    exit_info = fill.check_exit(t, candle(h=105, low=96, c=101), bars_open=5, config=CFG_CLEAN)
    assert exit_info == (101.0, "timeout")
    closed = fill.close_trade(t, 101.0, "timeout", 9000, CFG_CLEAN)
    # R = 20/100 = 0.2 → เกิน epsilon → สถานะ timeout (ไม่ใช่ be)
    assert closed.status == "timeout"


def test_break_even_status() -> None:
    t = fill.open_trade(sig(), CFG_CLEAN, 1000)
    closed = fill.close_trade(t, 100.1, "timeout", 9000, CFG_CLEAN)
    # R = (0.1*20)/100 = 0.02 < 0.05 → be
    assert closed.status == "be"
