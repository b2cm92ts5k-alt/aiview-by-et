"""AI orchestration (TDD.md §6): build context → call provider → parse Signal.

Pipeline: candles + indicators + MTF summary → prompt template
(ai/prompts/analyze.md) → provider.complete(json_mode) → pydantic validate →
one repair retry if the JSON is broken.
"""

from __future__ import annotations

import json
import time
import uuid
from pathlib import Path

from pydantic import ValidationError

from app.ai.base import AIProvider
from app.data.service import DataService
from app.indicators.base import candles_to_df
from app.indicators.basic import atr, rsi
from app.indicators.registry import compute_core
from app.indicators.zero_lag import zlema_trend
from app.models import Candle, Signal, Timeframe

PROMPT_PATH = Path(__file__).parent / "prompts" / "analyze.md"
CANDLES_IN_PROMPT = 40
CANDLES_FOR_INDICATORS = 300


class NoSetupError(Exception):
    """AI ตอบว่าไม่มี setup ที่สมเหตุสมผลตอนนี้ (ไม่ใช่ error ระบบ)."""


class SignalParseError(Exception):
    pass


def _split_prompt(template: str) -> tuple[str, str]:
    system, _, user = template.partition("# User")
    return system.replace("# System", "").strip(), user.strip()


def _fmt_candles(candles: list[Candle]) -> str:
    return "\n".join(
        f"{c.ts},{c.o:g},{c.h:g},{c.l:g},{c.c:g},{c.v:g}" for c in candles
    )


def _tf_summary(candles: list[Candle]) -> dict[str, float | str | None]:
    df = candles_to_df(candles)
    close = df["c"]
    trend_val = int(zlema_trend(close, 21).iloc[-1]) if len(close) >= 21 else 0
    trend = {1: "bullish", -1: "bearish", 0: "neutral"}[trend_val]
    rsi_v = rsi(close, 14).iloc[-1] if len(close) >= 15 else None
    atr_v = atr(df["h"], df["l"], close, 14).iloc[-1] if len(close) >= 15 else None
    return {
        "close": float(close.iloc[-1]),
        "trend": trend,
        "rsi14": round(float(rsi_v), 2) if rsi_v is not None else None,
        "atr14": round(float(atr_v), 6) if atr_v is not None else None,
    }


async def build_context(
    service: DataService, symbol: str, tfs: list[Timeframe]
) -> dict[str, str]:
    primary = tfs[0]
    primary_candles = await service.candles(symbol, primary, limit=CANDLES_FOR_INDICATORS)
    if not primary_candles:
        raise ValueError(f"no candles for {symbol} {primary}")

    mtf_lines = []
    for tf in tfs:
        candles = (
            primary_candles if tf == primary else await service.candles(symbol, tf, limit=60)
        )
        mtf_lines.append(f"- {tf}: {json.dumps(_tf_summary(candles))}")

    df = candles_to_df(primary_candles)
    results = compute_core(df)
    latest = {}
    for r in results:
        for line, values in r.lines.items():
            if values and values[-1] is not None:
                latest[line] = round(values[-1], 6)
    smc = next(r for r in results if r.name == "smc")
    structure = [
        f"- {m.kind} @ {m.price:g} (ts {m.ts})" for m in smc.markers[-8:]
    ] or ["- none detected"]

    return {
        "symbol": symbol,
        "primary_tf": primary,
        "mtf_context": "\n".join(mtf_lines),
        "candles": _fmt_candles(primary_candles[-CANDLES_IN_PROMPT:]),
        "indicators": json.dumps(latest),
        "structure": "\n".join(structure),
    }


def _parse_signal(
    text: str, symbol: str, tf: Timeframe, model: str
) -> Signal:
    try:
        raw = json.loads(text)
    except json.JSONDecodeError as e:
        raise SignalParseError(f"invalid JSON: {e}") from e
    if not isinstance(raw, dict):
        raise SignalParseError("expected a JSON object")
    if raw.get("side") is None:
        raise NoSetupError()
    tp_raw = raw.get("tp")
    if tp_raw is None:
        raise SignalParseError("missing tp")
    tp = [float(x) for x in tp_raw] if isinstance(tp_raw, list) else [float(tp_raw)]
    try:
        return Signal(
            id=str(uuid.uuid4()),
            symbol=symbol,
            tf=tf,
            side=raw["side"],
            entry=raw["entry"],
            sl=raw["sl"],
            tp=tp,
            rr=raw.get("rr") or 0.0,
            confidence=int(raw.get("confidence") or 0),
            reason=str(raw.get("reason") or ""),
            indicators_used={k: str(v) for k, v in (raw.get("indicators_used") or {}).items()},
            model=model,
            position_size_hint=raw.get("position_size_hint"),
            leverage_hint=raw.get("leverage_hint"),
            created_at=int(time.time() * 1000),
        )
    except (KeyError, TypeError, ValidationError) as e:
        raise SignalParseError(f"signal schema mismatch: {e}") from e


def build_context_from_candles(symbol: str, tf: Timeframe,
                               candles: list[Candle]) -> dict[str, str]:
    """สร้าง context จาก candles ที่เตรียมมาแล้ว (ใช้ใน benchmark walk-forward)."""
    if not candles:
        raise ValueError(f"no candles for {symbol} {tf}")
    df = candles_to_df(candles)
    results = compute_core(df)
    latest = {}
    for r in results:
        for line, values in r.lines.items():
            if values and values[-1] is not None:
                latest[line] = round(values[-1], 6)
    smc = next(r for r in results if r.name == "smc")
    structure = [f"- {m.kind} @ {m.price:g} (ts {m.ts})" for m in smc.markers[-8:]] or [
        "- none detected"
    ]
    return {
        "symbol": symbol,
        "primary_tf": tf,
        "mtf_context": f"- {tf}: {json.dumps(_tf_summary(candles))}",
        "candles": _fmt_candles(candles[-CANDLES_IN_PROMPT:]),
        "indicators": json.dumps(latest),
        "structure": "\n".join(structure),
    }


async def analyze_prepared(
    provider: AIProvider,
    model: str,
    symbol: str,
    tf: Timeframe,
    candles: list[Candle],
) -> Signal:
    """เหมือน analyze แต่ใช้ candles ที่ส่งมาเอง — สำหรับ benchmark historical."""
    ctx = build_context_from_candles(symbol, tf, candles)
    return await _complete_and_parse(provider, model, symbol, tf, ctx)


async def analyze(
    service: DataService,
    provider: AIProvider,
    model: str,
    symbol: str,
    tfs: list[Timeframe],
) -> Signal:
    ctx = await build_context(service, symbol, tfs)
    return await _complete_and_parse(provider, model, symbol, tfs[0], ctx)


async def _complete_and_parse(
    provider: AIProvider,
    model: str,
    symbol: str,
    primary_tf: Timeframe,
    ctx: dict[str, str],
) -> Signal:
    system, user = _split_prompt(PROMPT_PATH.read_text(encoding="utf-8"))
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": user.format(**ctx)},
    ]
    text = await provider.complete(model, messages, json_mode=True)
    try:
        return _parse_signal(text, symbol, primary_tf, model)
    except SignalParseError as first_error:
        # repair retry (TDD §6): ส่ง error กลับให้แก้เป็น JSON ที่ถูก
        messages += [
            {"role": "assistant", "content": text},
            {"role": "user",
             "content": f"Your response was invalid ({first_error}). "
                        "Respond again with ONLY the corrected JSON object."},
        ]
        text = await provider.complete(model, messages, json_mode=True)
        return _parse_signal(text, symbol, primary_tf, model)
