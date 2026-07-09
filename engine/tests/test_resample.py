from app.data.resample import StreamAggregator, resample_candles
from app.data.timeframes import TF_MS, bucket_start
from app.models import Candle

from .fakes import make_candles

TEN_M = TF_MS["10m"]
FIVE_M = TF_MS["5m"]


def _candle(ts: int, o: float, h: float, low: float, c: float, v: float) -> Candle:
    return Candle(symbol="BTC/USDT", tf="5m", ts=ts, o=o, h=h, l=low, c=c, v=v)


def test_batch_resample_5m_to_10m() -> None:
    t0 = (1_700_000_100_000 // TEN_M) * TEN_M  # align start to a 10m boundary
    base = make_candles("BTC/USDT", "5m", 6, start=t0)
    out = resample_candles(base, "10m")
    assert len(out) == 3
    first = out[0]
    assert first.tf == "10m"
    assert first.o == base[0].o
    assert first.c == base[1].c
    assert first.h == max(base[0].h, base[1].h)
    assert first.l == min(base[0].l, base[1].l)
    assert first.v == base[0].v + base[1].v
    assert first.ts % TEN_M == 0


def test_batch_resample_15m_to_45m_bar_count() -> None:
    base = make_candles("BTC/USDT", "15m", 9)
    out = resample_candles(base, "45m")
    # 9 × 15m ครอบ 45m ได้อย่างน้อย 3 แท่ง (แท่งขอบอาจไม่เต็ม)
    assert 3 <= len(out) <= 4
    assert all(c.tf == "45m" for c in out)


def test_bucket_start_1w_opens_monday() -> None:
    # 2023-11-15 (Wed) → week bucket must open Mon 2023-11-13 00:00 UTC
    wed = 1_700_000_100_000
    monday = bucket_start(wed, "1W")
    assert monday == 1_699_833_600_000
    assert (monday // 86_400_000 + 3) % 7 == 0  # epoch day 0 = Thu → Monday ⇔ day%7 == 4


def test_stream_aggregator_folds_updates() -> None:
    t0 = (1_700_000_100_000 // TEN_M) * TEN_M
    agg = StreamAggregator("10m")

    # forming base bar #1 sends cumulative updates → volume replaces, not adds
    c1 = agg.push(_candle(t0, 100, 101, 99, 100.5, 5))
    c2 = agg.push(_candle(t0, 100, 103, 98, 102.0, 8))
    assert c2.ts == t0 and c1.ts == t0
    assert c2.o == 100 and c2.h == 103 and c2.l == 98 and c2.c == 102.0
    assert c2.v == 8  # replaced, not 13

    # base bar #2 in the same 10m bucket → volume adds
    c3 = agg.push(_candle(t0 + FIVE_M, 102, 104, 101, 103.0, 4))
    assert c3.ts == t0
    assert c3.h == 104 and c3.l == 98 and c3.c == 103.0
    assert c3.v == 12  # 8 + 4

    # next bucket → fresh candle
    c4 = agg.push(_candle(t0 + TEN_M, 103, 105, 102, 104.0, 2))
    assert c4.ts == t0 + TEN_M
    assert c4.o == 103 and c4.v == 2


def test_stream_aggregator_calendar_year_bucket() -> None:
    agg = StreamAggregator("1Y")
    # 2023-06-01 monthly bar → bucket = 2023-01-01 UTC
    jun_2023 = 1_685_577_600_000
    jan_2023 = 1_672_531_200_000
    c = agg.push(Candle(symbol="X", tf="1M", ts=jun_2023, o=1, h=2, l=0.5, c=1.5, v=7))
    assert c.ts == jan_2023
    assert c.tf == "1Y"
