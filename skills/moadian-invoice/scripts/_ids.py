"""Check digits of Iranian identity numbers (stdlib only).

Sources (secondary — no official INTA/ssaa specification was reachable):
  X3a persian-tools (npm) 4.0.4, build/persian-tools.mjs: verifyIranianNationalId, verifyIranianLegalId
  X3b persian-tools (PyPI) 0.0.11, persian_tools/national_id, persian_tools/legal_id (+ their tests)
Two separate implementations with the same rules and test vectors. Because the
source is not official, validate_invoice.py reports failures as warnings.

National code «کد ملی» (10 digits, natural persons):
  s = Σ d[i]·(10−i) for i = 0..8;  r = s mod 11
  check digit d[9] == r if r < 2 else 11 − r
  invalid when digits 4–9 are all zero or all ten digits are the same.

Legal-entity national id «شناسه ملی اشخاص حقوقی» (11 digits):
  k = d[9] + 2;  s = Σ (d[i] + k)·w[i mod 5] for i = 0..9, w = 29, 27, 23, 19, 17
  check digit d[10] == s mod 11, with 10 counted as 0
  invalid when digits 4–9 are all zero.

Not checked (no sourced algorithm): 12-digit foreign-national codes, 14-digit
economic codes, civil-partnership ids (also 11 digits).
"""

from __future__ import annotations

import re

_ASCII_DIGITS = re.compile(r"[0-9]+")  # \d and str.isdigit() also match Persian/Arabic digits

_LEGAL_WEIGHTS = (29, 27, 23, 19, 17)


def national_code_ok(code: str) -> bool:
    if len(code) != 10 or not _ASCII_DIGITS.fullmatch(code) or len(set(code)) == 1 or int(code[3:9]) == 0:
        return False
    r = sum(int(code[i]) * (10 - i) for i in range(9)) % 11
    return int(code[9]) == (r if r < 2 else 11 - r)


def legal_id_ok(code: str) -> bool:
    if len(code) != 11 or not _ASCII_DIGITS.fullmatch(code) or int(code[3:9]) == 0:
        return False
    k = int(code[9]) + 2
    r = sum((int(code[i]) + k) * _LEGAL_WEIGHTS[i % 5] for i in range(10)) % 11
    return int(code[10]) == (0 if r == 10 else r)


def check(value, kind: str) -> str | None:
    """Return a problem description, or None if the value passes or is not checkable.

    kind: "national" (10 digits), "legal" (11 digits), or "auto" (10 → national, 11 → legal).
    """
    if not isinstance(value, str) or not _ASCII_DIGITS.fullmatch(value):
        return None  # type/format errors are reported by the field checks
    if kind == "auto":
        kind = {10: "national", 11: "legal"}.get(len(value), "")
    if kind == "national" and len(value) == 10 and not national_code_ok(value):
        return "fails the national-code (کد ملی) check digit"
    if kind == "legal" and len(value) == 11 and not legal_id_ok(value):
        return "fails the legal-entity national id (شناسه ملی) check digit"
    return None
