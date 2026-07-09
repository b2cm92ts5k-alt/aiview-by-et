"""Unit tests for Binance provider mapping — no network calls."""

from app.data.binance import CCXT_TF, _to_candle
from app.data.timeframes import RESAMPLE_BASE
from app.models import TIMEFRAMES


def test_ccxt_tf_mapping_complete() -> None:
    # ทุก app tf ต้องมีทาง: native บน Binance หรือ resample จาก base
    for tf in TIMEFRAMES:
        assert tf in CCXT_TF or tf in RESAMPLE_BASE, f"no path for {tf}"


def test_resample_bases_are_native() -> None:
    for target, base in RESAMPLE_BASE.items():
        assert base in CCXT_TF, f"{target} resamples from {base} which Binance lacks"


def test_to_candle_normalizes_row() -> None:
    row = [1_700_000_000_000, "1.5", 2.0, 1.0, 1.8, None]
    c = _to_candle("BTC/USDT", "5m", row)
    assert c.ts == 1_700_000_000_000
    assert c.o == 1.5 and c.v == 0.0
    assert c.symbol == "BTC/USDT"
