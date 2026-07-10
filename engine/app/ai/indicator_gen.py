"""Indicator-AI pipeline (F6): describe → AI generate DSL → validate on sample.

Validation = actually compute the definition on real candles; broken
expressions / unknown functions surface as DslError → one repair retry.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
from pydantic import ValidationError

from app.ai.base import AIProvider
from app.indicators.dsl import DslError, IndicatorDef, compute_def

PROMPT_PATH = Path(__file__).parent / "prompts" / "indicator.md"


class GenerationRefused(Exception):
    """AI ปฏิเสธ (เช่น ขอ copy proprietary indicator) — ไม่ใช่ error ระบบ."""


class GenerationError(Exception):
    pass


def _split_prompt(template: str) -> tuple[str, str]:
    system, _, user = template.partition("# User")
    return system.replace("# System", "").strip(), user.strip()


def parse_and_validate(text: str, sample: pd.DataFrame) -> IndicatorDef:
    try:
        raw = json.loads(text)
    except json.JSONDecodeError as e:
        raise GenerationError(f"invalid JSON: {e}") from e
    if not isinstance(raw, dict):
        raise GenerationError("expected a JSON object")
    if "error" in raw:
        raise GenerationRefused(str(raw["error"]))
    try:
        definition = IndicatorDef(**raw)
    except ValidationError as e:
        raise GenerationError(f"definition schema mismatch: {e}") from e
    try:
        compute_def(sample, definition)  # validate: ต้องรันบน sample ได้จริง
    except DslError as e:
        raise GenerationError(f"expression invalid: {e}") from e
    return definition


async def generate(
    provider: AIProvider,
    model: str,
    description: str,
    sample: pd.DataFrame,
) -> IndicatorDef:
    system, user = _split_prompt(PROMPT_PATH.read_text(encoding="utf-8"))
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": user.replace("{description}", description)},
    ]
    text = await provider.complete(model, messages, json_mode=True)
    try:
        return parse_and_validate(text, sample)
    except GenerationError as first_error:
        messages += [
            {"role": "assistant", "content": text},
            {"role": "user",
             "content": f"Your definition was invalid ({first_error}). "
                        "Respond again with ONLY the corrected JSON."},
        ]
        text = await provider.complete(model, messages, json_mode=True)
        return parse_and_validate(text, sample)
