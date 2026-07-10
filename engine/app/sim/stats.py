"""Trade statistics (TDD.md §7, FEATURES.md §F2).

Definitions (textbook):
- winrate  = wins / closed * 100
- avg R    = mean(r_multiple) of closed trades
- expectancy = avg R (R-based expectancy per trade)
- profit factor = gross profit / gross loss
- max drawdown % = largest peak-to-trough drop of the equity curve
"""

from __future__ import annotations

from collections.abc import Callable

from app.models import EquityPoint, SimConfig, Stats, StatsBreakdownRow, Trade


def _breakdown(trades: list[Trade], key: Callable[[Trade], str]) -> list[StatsBreakdownRow]:
    groups: dict[str, list[Trade]] = {}
    for t in trades:
        groups.setdefault(key(t), []).append(t)
    rows = []
    for k, group in sorted(groups.items()):
        wins = sum(1 for t in group if t.status == "win")
        rs = [t.r_multiple or 0.0 for t in group]
        rows.append(StatsBreakdownRow(
            key=k,
            trades=len(group),
            winrate=round(wins / len(group) * 100, 2),
            avg_r=round(sum(rs) / len(rs), 4),
            pnl=round(sum(t.pnl or 0.0 for t in group), 8),
        ))
    return rows


def compute_stats(trades: list[Trade], config: SimConfig, scope: str = "all") -> Stats:
    closed = sorted(
        (t for t in trades if t.status != "open" and t.closed_at is not None),
        key=lambda t: t.closed_at or 0,
    )
    wins = [t for t in closed if t.status == "win"]
    losses = [t for t in closed if t.status == "loss"]

    equity = config.initial_capital
    peak = equity
    max_dd = 0.0
    curve: list[EquityPoint] = []
    for t in closed:
        equity += t.pnl or 0.0
        peak = max(peak, equity)
        if peak > 0:
            max_dd = max(max_dd, (peak - equity) / peak * 100)
        curve.append(EquityPoint(ts=t.closed_at or 0, equity=round(equity, 8)))

    rs = [t.r_multiple or 0.0 for t in closed]
    gross_profit = sum(t.pnl or 0.0 for t in closed if (t.pnl or 0.0) > 0)
    gross_loss = abs(sum(t.pnl or 0.0 for t in closed if (t.pnl or 0.0) < 0))

    return Stats(
        scope=scope,
        trades=len(closed),
        wins=len(wins),
        losses=len(losses),
        winrate=round(len(wins) / len(closed) * 100, 2) if closed else 0.0,
        avg_r=round(sum(rs) / len(rs), 4) if rs else 0.0,
        expectancy=round(sum(rs) / len(rs), 4) if rs else 0.0,
        profit_factor=round(gross_profit / gross_loss, 4) if gross_loss > 0 else 0.0,
        max_drawdown_pct=round(max_dd, 4),
        total_pnl=round(sum(t.pnl or 0.0 for t in closed), 8),
        equity_curve=curve,
        by_symbol=_breakdown(closed, lambda t: t.symbol),
        by_tf=_breakdown(closed, lambda t: t.tf),
        by_model=_breakdown(closed, lambda t: t.model),
        by_side=_breakdown(closed, lambda t: t.side),
    )
