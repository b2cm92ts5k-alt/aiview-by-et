"""Indicator DSL — safe expression language for AI-generated indicators (F6).

Security model (spec.md Decisions 2026-07-10): AI ออก "config" ไม่ใช่โค้ด —
expression ถูก parse ด้วย `ast` แล้วตีความเองบน whitelist เท่านั้น:
ไม่มี attribute access, ไม่มี subscript, ไม่มี import, เรียกได้เฉพาะฟังก์ชัน
ใน FUNCTIONS. ป้องกัน arbitrary code execution จาก LLM output.

Expression มองทุกอย่างเป็น pandas Series (elementwise) เช่น
    "ema(c, fast) - ema(c, slow)"
    "crossover(zlema(c, 21), sma(c, 50)) & (rsi(c, 14) < 70)"
"""

from __future__ import annotations

import ast
import math
import re
from typing import Any

import pandas as pd
from pydantic import BaseModel, field_validator

from app.indicators import basic, zero_lag
from app.indicators.base import IndicatorResult

MAX_EXPR_LEN = 500
MAX_LINES = 12
NAME_RE = re.compile(r"^[a-z][a-z0-9_]{1,40}$")


# ---------- DSL definition schema ----------


class IndicatorDef(BaseModel):
    """AI-generated indicator definition (stored in indicator_defs)."""

    name: str  # slug, unique
    title: str
    description: str  # methodology อธิบายเป็นข้อความ (คนอ่าน)
    source: str  # public methodology ที่อ้างอิง — บังคับมี (legal guardrail)
    params: dict[str, float] = {}
    lines: dict[str, str] = {}  # line name -> expression (วาดบน chart)
    long_when: str | None = None  # boolean expression → ใช้เป็น strategy ได้
    short_when: str | None = None

    @field_validator("name")
    @classmethod
    def _name_slug(cls, v: str) -> str:
        if not NAME_RE.match(v):
            raise ValueError("name must be a lowercase slug (a-z, 0-9, _)")
        return v

    @field_validator("lines")
    @classmethod
    def _lines_bound(cls, v: dict[str, str]) -> dict[str, str]:
        if not v:
            raise ValueError("at least one line required")
        if len(v) > MAX_LINES:
            raise ValueError(f"too many lines (max {MAX_LINES})")
        for name in v:
            if not NAME_RE.match(name):
                raise ValueError(f"bad line name: {name}")
        return v


# ---------- safe evaluator ----------


def _series(x: Any, like: pd.Series) -> pd.Series:
    if isinstance(x, pd.Series):
        return x
    return pd.Series(float(x), index=like.index)


def _crossover(a: Any, b: Any) -> pd.Series:
    sa, sb = (a if isinstance(a, pd.Series) else None), (b if isinstance(b, pd.Series) else None)
    ref = sa if sa is not None else sb
    if ref is None:
        raise DslError("crossover needs at least one series")
    a, b = _series(a, ref), _series(b, ref)
    return (a > b) & (a.shift(1) <= b.shift(1))


def _crossunder(a: Any, b: Any) -> pd.Series:
    ref = a if isinstance(a, pd.Series) else b
    a, b = _series(a, ref), _series(b, ref)
    return (a < b) & (a.shift(1) >= b.shift(1))


FUNCTIONS: dict[str, Any] = {
    "ema": lambda x, n: basic.ema(x, int(n)),
    "sma": lambda x, n: basic.sma(x, int(n)),
    "rma": lambda x, n: basic.rma(x, int(n)),
    "rsi": lambda x, n: basic.rsi(x, int(n)),
    "zlema": lambda x, n: zero_lag.zlema(x, int(n)),
    "shift": lambda x, n: x.shift(int(n)),
    "highest": lambda x, n: x.rolling(int(n)).max(),
    "lowest": lambda x, n: x.rolling(int(n)).min(),
    "abs": lambda x: x.abs() if isinstance(x, pd.Series) else abs(x),
    "crossover": _crossover,
    "crossunder": _crossunder,
    # atr ใช้ h/l/c จาก context — inject ตอน eval (ดู _Evaluator.call)
}

_BIN_OPS: dict[type[ast.operator], Any] = {
    ast.Add: lambda a, b: a + b,
    ast.Sub: lambda a, b: a - b,
    ast.Mult: lambda a, b: a * b,
    ast.Div: lambda a, b: a / b,
}

_CMP_OPS: dict[type[ast.cmpop], Any] = {
    ast.Gt: lambda a, b: a > b,
    ast.Lt: lambda a, b: a < b,
    ast.GtE: lambda a, b: a >= b,
    ast.LtE: lambda a, b: a <= b,
}


class DslError(ValueError):
    pass


class _Evaluator(ast.NodeVisitor):
    def __init__(self, env: dict[str, Any], df: pd.DataFrame):
        self.env = env
        self.df = df

    def eval(self, node: ast.AST) -> Any:
        return self.visit(node)

    def visit_Expression(self, node: ast.Expression) -> Any:
        return self.eval(node.body)

    def visit_Constant(self, node: ast.Constant) -> Any:
        if isinstance(node.value, (int, float)):
            return float(node.value)
        raise DslError(f"literal not allowed: {node.value!r}")

    def visit_Name(self, node: ast.Name) -> Any:
        if node.id in self.env:
            return self.env[node.id]
        raise DslError(f"unknown name: {node.id}")

    def visit_BinOp(self, node: ast.BinOp) -> Any:
        op = _BIN_OPS.get(type(node.op))
        if op is None:
            raise DslError(f"operator not allowed: {type(node.op).__name__}")
        return op(self.eval(node.left), self.eval(node.right))

    def visit_UnaryOp(self, node: ast.UnaryOp) -> Any:
        if isinstance(node.op, ast.USub):
            return -self.eval(node.operand)
        if isinstance(node.op, ast.Invert):
            return ~self.eval(node.operand)
        raise DslError(f"unary op not allowed: {type(node.op).__name__}")

    def visit_Compare(self, node: ast.Compare) -> Any:
        if len(node.ops) != 1:
            raise DslError("chained comparison not allowed")
        op = _CMP_OPS.get(type(node.ops[0]))
        if op is None:
            raise DslError(f"comparison not allowed: {type(node.ops[0]).__name__}")
        return op(self.eval(node.left), self.eval(node.comparators[0]))

    def visit_BoolOp(self, node: ast.BoolOp) -> Any:
        raise DslError("use & / | instead of and / or")

    def visit_Call(self, node: ast.Call) -> Any:
        if not isinstance(node.func, ast.Name):
            raise DslError("only plain function calls allowed")
        fname = node.func.id
        if node.keywords:
            raise DslError("keyword arguments not allowed")
        args = [self.eval(a) for a in node.args]
        if fname == "atr":
            if len(args) != 1:
                raise DslError("atr(period) takes 1 argument")
            return basic.atr(self.df["h"], self.df["l"], self.df["c"], int(args[0]))
        fn = FUNCTIONS.get(fname)
        if fn is None:
            raise DslError(f"unknown function: {fname}")
        try:
            return fn(*args)
        except DslError:
            raise
        except Exception as e:
            raise DslError(f"{fname}(): {e}") from e

    def generic_visit(self, node: ast.AST) -> Any:
        # ทุก node ที่ไม่ได้ whitelist ไว้ = ปฏิเสธ (Attribute/Subscript/Lambda/...)
        raise DslError(f"syntax not allowed: {type(node).__name__}")


def _eval_expr(expr: str, env: dict[str, Any], df: pd.DataFrame) -> Any:
    if len(expr) > MAX_EXPR_LEN:
        raise DslError("expression too long")
    try:
        tree = ast.parse(expr, mode="eval")
    except SyntaxError as e:
        raise DslError(f"syntax error: {e.msg}") from e
    return _EvaluatorWithBitwise(env, df).eval(tree)


class _EvaluatorWithBitwise(_Evaluator):
    def visit_BinOp(self, node: ast.BinOp) -> Any:
        if isinstance(node.op, (ast.BitAnd, ast.BitOr)):
            a, b = self.eval(node.left), self.eval(node.right)
            return (a & b) if isinstance(node.op, ast.BitAnd) else (a | b)
        return super().visit_BinOp(node)


def compute_def(df: pd.DataFrame, definition: IndicatorDef) -> IndicatorResult:
    """คำนวณ IndicatorDef บน OHLCV → IndicatorResult (+ boolean line long/short)."""
    env: dict[str, Any] = {
        "o": df["o"], "h": df["h"], "l": df["l"], "c": df["c"], "v": df["v"],
        **{k: float(v) for k, v in definition.params.items()},
    }
    lines: dict[str, list[float | None]] = {}
    for name, expr in definition.lines.items():
        value = _eval_expr(expr, env, df)
        if not isinstance(value, pd.Series):
            value = _series(value, df["c"])
        env[name] = value  # line ก่อนหน้าอ้างต่อได้
        lines[name] = _to_list(value)

    signal_exprs: list[tuple[str, str | None]] = [
        ("long", definition.long_when), ("short", definition.short_when),
    ]
    for label, sig_expr in signal_exprs:
        if sig_expr:
            sig = _eval_expr(sig_expr, env, df)
            if not isinstance(sig, pd.Series):
                raise DslError(f"{label}_when must produce a series")
            lines[f"signal_{label}"] = _to_list(sig.astype(float))

    return IndicatorResult(name=definition.name, lines=lines)


def _to_list(series: pd.Series) -> list[float | None]:
    out: list[float | None] = []
    for v in series.tolist():
        if v is None or (isinstance(v, float) and (math.isnan(v) or math.isinf(v))):
            out.append(None)
        else:
            out.append(float(v))
    return out
