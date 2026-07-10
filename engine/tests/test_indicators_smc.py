import pandas as pd

from app.indicators.smc import fvg_markers, order_block_markers, structure_markers, swing_points


def df_from(rows: list[tuple[float, float, float, float]]) -> pd.DataFrame:
    """rows = (o, h, l, c); ts = index*1000."""
    return pd.DataFrame(
        [{"ts": i * 1000, "o": o, "h": h, "l": low, "c": c, "v": 1.0}
         for i, (o, h, low, c) in enumerate(rows)]
    )


def test_swing_points_detects_fractals() -> None:
    #                     0        1        2 (peak)   3        4
    df = df_from([(1, 2, 1, 1), (2, 3, 2, 2), (3, 5, 3, 4), (2, 3, 2, 2), (1, 2, 1, 1)])
    highs, lows = swing_points(df, k=2)
    assert highs == [2]
    assert lows == []


def test_swing_lows() -> None:
    df = df_from([(3, 4, 3, 3), (2, 3, 2, 2), (1, 2, 0.5, 1), (2, 3, 2, 2), (3, 4, 3, 3)])
    highs, lows = swing_points(df, k=2)
    assert lows == [2]


def test_bos_up_when_close_breaks_swing_high() -> None:
    # swing high 5 ที่ i=2 (ยืนยันหลัง i>=4) → i=5 close 6 > 5 → BOS up แรก
    df = df_from([
        (1, 2, 1, 1), (2, 3, 2, 2), (3, 5, 3, 4), (2, 3, 2, 2), (1, 2, 1, 1),
        (2, 6.5, 2, 6),
    ])
    marks = structure_markers(df, k=2)
    assert [m.kind for m in marks] == ["bos_up"]
    assert marks[0].price == 5.0
    assert marks[0].ts == 5000


def test_choch_down_after_uptrend() -> None:
    # BOS up ก่อน (trend=+1) แล้ว close หลุด swing low → choch_down
    df = df_from([
        (1, 2, 1, 1), (2, 3, 2, 2), (3, 5, 3, 4), (2, 3, 2, 2), (1, 2, 1.5, 1.6),
        (2, 6.5, 2, 6),      # i=5: bos_up @5
        (6, 6.2, 5, 5.5), (5, 5.5, 4, 4.5), (4, 4.6, 1.2, 1.4),  # โครงสร้างย่อลง
        (1.4, 1.5, 0.8, 0.9),  # i=9: close 0.9 < swing low 1.5(i=4)? — 1.5 confirmed ที่ i>=6
    ])
    marks = structure_markers(df, k=2)
    kinds = [m.kind for m in marks]
    assert kinds[0] == "bos_up"
    assert "choch_down" in kinds


def test_fvg_bullish_gap() -> None:
    # candle0 high=2, candle2 low=3 → bullish FVG zone (2,3) ที่ candle1
    df = df_from([(1, 2, 1, 2), (2, 4, 2, 4), (4, 6, 3, 5)])
    marks = fvg_markers(df)
    assert len(marks) == 1
    m = marks[0]
    assert m.kind == "fvg_bull" and m.ts == 1000
    assert (m.price, m.price2) == (2.0, 3.0)


def test_fvg_bearish_gap() -> None:
    df = df_from([(6, 6, 4, 4), (4, 3.5, 2, 2), (2, 1.5, 1, 1)])
    marks = fvg_markers(df)
    assert [m.kind for m in marks] == ["fvg_bear"]


def test_order_block_last_down_candle_before_bos_up() -> None:
    df = df_from([
        (1, 2, 1, 1), (2, 3, 2, 2), (3, 5, 3, 4), (3, 3.5, 2.5, 2.6),  # i=3 down candle
        (2.6, 3, 2.4, 2.8),
        (2.8, 6.5, 2.7, 6),  # i=5 bos_up
    ])
    obs = order_block_markers(df, k=2)
    assert len(obs) == 1
    ob = obs[0]
    assert ob.kind == "ob_bull"
    assert ob.ts == 3000  # last down candle before the break
    assert (ob.price, ob.price2) == (2.5, 3.5)
