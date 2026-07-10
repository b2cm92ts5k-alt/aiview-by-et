import pandas as pd
import pytest

from app.indicators import basic
from app.indicators.dsl import DslError, IndicatorDef, _eval_expr, compute_def

from .fakes import make_candles


def df() -> pd.DataFrame:
    from app.indicators.base import candles_to_df

    return candles_to_df(make_candles("BTC/USDT", "15m", 60))


def env(d: pd.DataFrame) -> dict:
    return {"o": d["o"], "h": d["h"], "l": d["l"], "c": d["c"], "v": d["v"]}


# ---------- correctness ----------


def test_ema_expr_matches_builtin() -> None:
    d = df()
    out = _eval_expr("ema(c, 20)", env(d), d)
    pd.testing.assert_series_equal(out, basic.ema(d["c"], 20))


def test_arithmetic_and_params() -> None:
    d = df()
    e = {**env(d), "fast": 5.0, "slow": 10.0}
    out = _eval_expr("ema(c, fast) - ema(c, slow)", e, d)
    expected = basic.ema(d["c"], 5) - basic.ema(d["c"], 10)
    pd.testing.assert_series_equal(out, expected)


def test_crossover_boolean() -> None:
    d = df()
    out = _eval_expr("crossover(ema(c, 3), ema(c, 30)) & (rsi(c, 14) < 90)", env(d), d)
    assert out.dtype == bool


def test_atr_uses_ohlc_context() -> None:
    d = df()
    out = _eval_expr("atr(14)", env(d), d)
    pd.testing.assert_series_equal(out, basic.atr(d["h"], d["l"], d["c"], 14))


def test_lines_can_reference_earlier_lines() -> None:
    d = df()
    definition = IndicatorDef(
        name="macd_like", title="t", description="d", source="Appel MACD (public)",
        params={"fast": 12, "slow": 26},
        lines={"macd": "ema(c, fast) - ema(c, slow)", "sig": "ema(macd, 9)"},
    )
    result = compute_def(d, definition)
    assert set(result.lines) == {"macd", "sig"}
    assert len(result.lines["macd"]) == len(d)


def test_signal_lines_emitted() -> None:
    d = df()
    definition = IndicatorDef(
        name="xover_sig", title="t", description="d", source="public",
        lines={"fastl": "ema(c, 3)"},
        long_when="crossover(fastl, ema(c, 30))",
        short_when="crossunder(fastl, ema(c, 30))",
    )
    result = compute_def(d, definition)
    assert "signal_long" in result.lines and "signal_short" in result.lines


# ---------- security ----------


@pytest.mark.parametrize("expr", [
    "__import__('os').system('dir')",
    "c.__class__",
    "getattr(c, 'values')",
    "(lambda: 1)()",
    "c[0]",
    "open('x')",
    "exec('1')",
    "[x for x in c]",
    "c.sum()",
    "'hello'",
])
def test_dangerous_expressions_rejected(expr: str) -> None:
    d = df()
    with pytest.raises(DslError):
        _eval_expr(expr, env(d), d)


def test_unknown_name_rejected() -> None:
    d = df()
    with pytest.raises(DslError, match="unknown name"):
        _eval_expr("secret_var + 1", env(d), d)


def test_expression_length_capped() -> None:
    d = df()
    with pytest.raises(DslError, match="too long"):
        _eval_expr("c" + " + c" * 300, env(d), d)


def test_bad_def_name_rejected() -> None:
    with pytest.raises(ValueError):
        IndicatorDef(name="Bad Name!", title="t", description="d", source="s",
                     lines={"a": "c"})


def test_too_many_lines_rejected() -> None:
    with pytest.raises(ValueError):
        IndicatorDef(name="many_lines", title="t", description="d", source="s",
                     lines={f"l{i}": "c" for i in range(20)})
