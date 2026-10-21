"""Shared helpers for validate_invoice.py and _arith.py (report, numbers, code hints)."""

from __future__ import annotations

from decimal import ROUND_DOWN, Decimal, InvalidOperation

import explain_error

FIELD_NO = {name: no for no, name in explain_error.load_field_numbers().items()}
HUNDRED = Decimal(100)


def trunc(x: Decimal, places: int = 0) -> Decimal:
    """S1 general rule 1: amounts are truncated («روش قطع کردن»), never rounded."""
    return x.quantize(Decimal(1).scaleb(-places), rounding=ROUND_DOWN)


def code_hint(field: str, check_type: str, detail: str = "") -> str | None:
    """Likely system code per the K T FFF DD scheme (references/errors.md §2)."""
    no = FIELD_NO.get(field)
    return f"0{check_type}{no}{detail}" if no else None


class Report:
    def __init__(self) -> None:
        self.errors: list[dict] = []
        self.warnings: list[dict] = []
        self.notes: list[str] = []

    def add(self, severity, path, message, rule, source, expected=None, actual=None, code=None):
        item = {"path": path, "message": message, "rule": rule, "source": source}
        if expected is not None or actual is not None:
            item["expected"], item["actual"] = _plain(expected), _plain(actual)
        if code:
            item["code_hint"] = code
        (self.errors if severity == "error" else self.warnings).append(item)

    def error(self, *a, **k):
        self.add("error", *a, **k)

    def warn(self, *a, **k):
        self.add("warning", *a, **k)


def _plain(v):
    if isinstance(v, Decimal):
        return int(v) if v == v.to_integral_value() else float(v)
    return v


def num(v) -> Decimal | None:
    if v is None or isinstance(v, bool):
        return None
    try:
        return Decimal(str(v))
    except (InvalidOperation, ValueError):
        return None
