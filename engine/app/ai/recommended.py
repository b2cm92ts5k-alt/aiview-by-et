"""Tag "⭐ แนะนำ" ต่อ model — mapping จาก docs/AI_MODELS.md (ผู้ใช้เคาะ 2026-07-10).

ห้ามแก้ pattern โดยไม่ถามผู้ใช้ (MEMORY.md: ตัวเลข/รุ่นใน AI_MODELS.md เป็น anchor).
match แบบ substring/regex บน model id เพราะ id จริงมี suffix วันที่/เวอร์ชัน.
"""

from __future__ import annotations

import re

# provider -> list of regex (case-insensitive) ที่ถือว่า "แนะนำ"
_RECOMMENDED: dict[str, list[str]] = {
    "anthropic": [r"opus", r"sonnet"],
    "openai": [r"gpt-5(?!.*mini)", r"^o\d"],
    "google": [r"gemini.*pro"],
    "openrouter": [],
    "github": [],
    "ollama": [r"qwen[23][^ ]*:?(14|32)b", r"deepseek-r1"],
}


def is_recommended(provider: str, model_id: str) -> bool:
    patterns = _RECOMMENDED.get(provider, [])
    return any(re.search(p, model_id, re.IGNORECASE) for p in patterns)
