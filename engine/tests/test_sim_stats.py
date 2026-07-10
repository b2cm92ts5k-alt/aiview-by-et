import pytest

from app.models import SimConfig, Trade
from app.sim.stats import compute_stats

CFG = SimConfig(initial_capital=1000)


def trade(pnl: float, r: float, status: str, closed_at: int, symbol: str = "BTC/USDT",
          tf: str = "15m", model: str = "m", side: str = "long") -> Trade:
    return Trade(id=f"t{closed_at}", signal_id="s", symbol=symbol, tf=tf,  # type: ignore[arg-type]
                 side=side, entry=100, exit=100 + pnl, sl=95, tp=110, qty=1,
                 pnl=pnl, r_multiple=r, status=status, model=model,
                 opened_at=closed_at - 100, closed_at=closed_at)


def test_stats_hand_computed() -> None:
    trades = [
        trade(+200, +2.0, "win", 1000),
        trade(-100, -1.0, "loss", 2000),
        trade(+100, +1.0, "win", 3000),
        trade(-100, -1.0, "loss", 4000),
    ]
    s = compute_stats(trades, CFG)
    assert s.trades == 4 and s.wins == 2 and s.losses == 2
    assert s.winrate == pytest.approx(50.0)
    assert s.avg_r == pytest.approx(0.25)  # (2-1+1-1)/4
    assert s.expectancy == pytest.approx(0.25)
    assert s.profit_factor == pytest.approx(1.5)  # 300/200
    assert s.total_pnl == pytest.approx(100.0)


def test_equity_curve_and_drawdown() -> None:
    trades = [
        trade(+200, 2, "win", 1000),   # equity 1200 (peak)
        trade(-300, -3, "loss", 2000),  # equity 900 → DD = 300/1200 = 25%
        trade(+150, 1.5, "win", 3000),  # equity 1050
    ]
    s = compute_stats(trades, CFG)
    assert [p.equity for p in s.equity_curve] == [1200, 900, 1050]
    assert s.max_drawdown_pct == pytest.approx(25.0)


def test_open_trades_excluded() -> None:
    t_open = Trade(id="o1", signal_id="s", symbol="BTC/USDT", tf="15m", side="long",
                   entry=100, sl=95, tp=110, qty=1, model="m", opened_at=1,
                   status="open")
    s = compute_stats([t_open, trade(100, 1, "win", 1000)], CFG)
    assert s.trades == 1


def test_breakdowns() -> None:
    trades = [
        trade(+100, 1, "win", 1000, model="qwen3:8b"),
        trade(-100, -1, "loss", 2000, model="qwen3:8b"),
        trade(+200, 2, "win", 3000, model="rule:zlema-smc", side="short"),
    ]
    s = compute_stats(trades, CFG)
    by_model = {r.key: r for r in s.by_model}
    assert by_model["qwen3:8b"].trades == 2
    assert by_model["qwen3:8b"].winrate == pytest.approx(50.0)
    assert by_model["rule:zlema-smc"].pnl == pytest.approx(200.0)
    by_side = {r.key: r for r in s.by_side}
    assert by_side["long"].trades == 2 and by_side["short"].trades == 1


def test_empty_trades_all_zero() -> None:
    s = compute_stats([], CFG)
    assert s.trades == 0 and s.winrate == 0.0 and s.equity_curve == []
