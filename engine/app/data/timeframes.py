"""Timeframe model (ARCHITECTURE.md §6).

Fixed-length tfs get an exact ms width. Calendar tfs (1M/1Y) have no fixed
width — bucketing for them is calendar-based (see resample.py).
"""

from __future__ import annotations

from app.models import Timeframe

MINUTE_MS = 60_000
HOUR_MS = 60 * MINUTE_MS
DAY_MS = 24 * HOUR_MS

# fixed-width tfs only — 1M/1Y intentionally absent
TF_MS: dict[Timeframe, int] = {
    "5m": 5 * MINUTE_MS,
    "10m": 10 * MINUTE_MS,
    "15m": 15 * MINUTE_MS,
    "30m": 30 * MINUTE_MS,
    "45m": 45 * MINUTE_MS,
    "60m": HOUR_MS,
    "4h": 4 * HOUR_MS,
    "1D": DAY_MS,
    "1W": 7 * DAY_MS,
}

# tf ที่ provider ส่วนใหญ่ไม่มีตรงๆ → resample จาก base ที่เล็กกว่า (TDD §4)
RESAMPLE_BASE: dict[Timeframe, Timeframe] = {
    "10m": "5m",
    "45m": "15m",
    "1Y": "1M",
}


def bucket_start(ts: int, tf: Timeframe) -> int:
    """Bar-open timestamp of the bucket containing ts (fixed-width tfs only)."""
    width = TF_MS[tf]
    if tf == "1W":
        # epoch day 0 = Thursday → Monday = day 4 (mod 7); shift so weeks open Monday 00:00 UTC
        monday_offset = 4 * DAY_MS
        return ((ts - monday_offset) // width) * width + monday_offset
    return (ts // width) * width
