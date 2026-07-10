"""Timeframe resampling (TDD.md §4): batch via pandas + streaming aggregator."""

from __future__ import annotations

import pandas as pd

from app.data.timeframes import TF_MS, bucket_start
from app.models import Candle, Timeframe

# pandas offset aliases per target tf (calendar tfs use period rules)
_PANDAS_RULE: dict[Timeframe, str] = {
    "5m": "5min",
    "10m": "10min",
    "15m": "15min",
    "30m": "30min",
    "45m": "45min",
    "60m": "1h",
    "4h": "4h",
    "1D": "1D",
    "1W": "W-MON",
    "1M": "MS",
    "1Y": "YS",
}


def resample_candles(candles: list[Candle], target_tf: Timeframe) -> list[Candle]:
    """Aggregate base-tf candles into target_tf. Input must be oldest→newest."""
    if not candles:
        return []
    df = pd.DataFrame([c.model_dump() for c in candles])
    df["dt"] = pd.to_datetime(df["ts"], unit="ms", utc=True)
    df = df.set_index("dt")

    rule = _PANDAS_RULE[target_tf]
    agg = df.resample(rule, label="left", closed="left").agg(
        {"o": "first", "h": "max", "l": "min", "c": "last", "v": "sum"}
    )
    agg = agg.dropna(subset=["o"])

    symbol = candles[0].symbol
    return [
        Candle(
            symbol=symbol,
            tf=target_tf,
            ts=int(idx.timestamp() * 1000),
            o=row["o"],
            h=row["h"],
            l=row["l"],
            c=row["c"],
            v=row["v"],
        )
        for idx, row in agg.iterrows()
    ]


class StreamAggregator:
    """Fold a stream of base-tf candle updates into the forming target-tf candle.

    Calendar tfs (1M/1Y) bucket by UTC month/year start instead of fixed width.
    """

    def __init__(self, target_tf: Timeframe):
        self.tf = target_tf
        self._current: Candle | None = None
        # forming base bars re-send cumulative volume → keep latest per base ts
        self._base_vols: dict[int, float] = {}
        self._hi = 0.0
        self._lo = 0.0

    def _bucket(self, ts: int) -> int:
        if self.tf in TF_MS:
            return bucket_start(ts, self.tf)
        dt = pd.Timestamp(ts, unit="ms", tz="UTC")
        if self.tf == "1M":
            start = dt.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        else:  # 1Y
            start = dt.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        return int(start.timestamp() * 1000)

    def push(self, base: Candle) -> Candle:
        """Merge a base-tf update; returns the current forming target candle."""
        bucket = self._bucket(base.ts)
        cur = self._current
        if cur is None or cur.ts != bucket:
            self._base_vols = {base.ts: base.v}
            self._hi, self._lo = base.h, base.l
            self._current = Candle(
                symbol=base.symbol, tf=self.tf, ts=bucket,
                o=base.o, h=base.h, l=base.l, c=base.c, v=base.v,
            )
            return self._current

        self._base_vols[base.ts] = base.v
        self._hi = max(self._hi, base.h)
        self._lo = min(self._lo, base.l)
        self._current = Candle(
            symbol=cur.symbol, tf=self.tf, ts=cur.ts,
            o=cur.o, h=self._hi, l=self._lo, c=base.c, v=sum(self._base_vols.values()),
        )
        return self._current
