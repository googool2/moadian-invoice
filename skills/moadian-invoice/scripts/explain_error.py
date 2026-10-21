#!/usr/bin/env python3
"""Explain a Moadian error code using references/errors.md.

Usage:
    python scripts/explain_error.py 0300101
    python scripts/explain_error.py 0301               # short form, mapped via errors.md section 7
    python scripts/explain_error.py "duplicate"        # search messages
    python scripts/explain_error.py --from-response resp.json
    python scripts/explain_error.py --list

Reads only the local errors.md table (no network). Output is JSON. A code that
is not in the table is reported as unknown, plus a structural decode of the
7-digit scheme (error/warning, check type, field) from errors.md section 2/5, which follow
the official RC_TXPS.EC_V02 tables.
This script never invents a meaning beyond that.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import _cli

ERRORS_MD = Path(__file__).resolve().parent.parent / "references" / "errors.md"
COLUMNS = ("code", "message_fa", "meaning_en", "fields", "fix", "source")
_PERSIAN_DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")


def normalize_code(text: str) -> str:
    return re.sub(r"\s+", "", str(text).translate(_PERSIAN_DIGITS))


def load_table(path: Path = ERRORS_MD) -> list[dict]:
    """Parse every markdown table row whose first cell looks like a code."""
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line.startswith("|") or set(line) <= set("|-: "):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        code = cells[0].strip("`")
        if not code or code.lower() == "code" or len(cells) < len(COLUMNS):
            continue
        row = dict(zip(COLUMNS, cells[: len(COLUMNS)]))
        row["code"] = code
        row["unverified"] = "[UNVERIFIED" in line
        rows.append(row)
    return rows


CHECK_TYPES = {
    "0": "field is empty",
    "1": "JSON structure (format/regex/enum/type/range)",
    "2": "calculation or logic rule failed",
    "3": "does not match system data",
    "4": "field sent out of pattern (not expected for this invoice pattern)",
    "5": "duplicate",
}
STRUCT_DETAIL = {
    "01": "disallowed property", "02": "not an allowed value (enum)", "03": "wrong type",
    "04": "regex/length", "05": "exclusive max/min", "06": "max/min", "09": "too many decimal places",
    "10": "invalid JSON (with field 000)",
}
SECTIONS = {"000": "whole JSON", "500": "header", "600": "body", "700": "payments", "800": "extension"}


def load_field_numbers(path: Path = ERRORS_MD) -> dict[str, str]:
    text = path.read_text(encoding="utf-8")
    m = re.search(r"^## 5\..*?$(.*?)(^## |\Z)", text, re.S | re.M)
    return dict(re.findall(r"\b(\d{3}) ([a-z0-9]+)\b", m.group(1))) if m else {}


def load_aliases(path: Path = ERRORS_MD) -> dict[str, str]:
    """Short forms (errors.md section 7): {"0301": "0300101", ...}."""
    text = path.read_text(encoding="utf-8")
    m = re.search(r"^## 7\..*?$(.*?)(^## |\Z)", text, re.S | re.M)
    return dict(re.findall(r"^\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*$", m.group(1), re.M)) if m else {}


def decode_structure(code: str, fields: dict[str, str]) -> dict | None:
    """Decode K T FFF [DD] (errors.md section 2). Returns None if not that shape."""
    c = normalize_code(code)
    if not re.fullmatch(r"[01][0-5]\d{3}(\d{2})?", c):
        return None
    if len(c) == 5 and c[:2] in ("04", "05"):
        # 04111..04153 / 05139.. are packet/transport codes, not K T FFF (errors.md section 3)
        return None
    k, t, fff, dd = c[0], c[1], c[2:5], c[5:7]
    out = {
        "severity": "error (invoice rejected)" if k == "0" else "warning (invoice still accepted)",
        "check_type": CHECK_TYPES[t],
        "field_number": fff,
        "field": SECTIONS.get(fff) or fields.get(fff, "unknown field number"),
        "detail": dd or None,
        "basis": "numbering scheme in errors.md section 2 (official RC_TXPS.EC_V02 Table 7)",
    }
    if t == "1" and dd:
        out["detail_meaning"] = STRUCT_DETAIL.get(dd, "unknown detail")
    return out


def lookup(query: str, rows: list[dict]) -> list[dict]:
    q = normalize_code(query)
    exact = [r for r in rows if normalize_code(r["code"]).lower() == q.lower()]
    if exact:
        return exact
    needle = str(query).strip().lower()
    return [
        r for r in rows
        if needle and any(needle in r[k].lower() for k in ("code", "message_fa", "meaning_en", "fields"))
    ]


def codes_from_response(data) -> list[str]:
    """Collect error codes from an inquiry response (any nesting)."""
    found: list[str] = []

    def walk(node):
        if isinstance(node, dict):
            for key in ("code", "errorCode", "error_code"):
                if key in node and node[key] not in (None, ""):
                    found.append(str(node[key]))
            for v in node.values():
                walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)

    walk(data)
    return list(dict.fromkeys(found))


def explain(queries: list[str], rows: list[dict], fields: dict[str, str] | None = None,
            aliases: dict[str, str] | None = None) -> dict:
    fields = fields if fields is not None else {}
    aliases = aliases if aliases is not None else {}
    results = []
    for q in queries:
        full = aliases.get(normalize_code(q))
        matches = lookup(full or q, rows)
        results.append({
            "query": q,
            "short_form_of": full,
            "found": bool(matches),
            "matches": matches,
            "structure": decode_structure(full or q, fields),
            "note": None if matches else (
                "Not in references/errors.md. Do not guess a meaning beyond 'structure': quote "
                "the raw message from the response and check the current INTA error list (EC_V02)."
            ),
        })
    return {"source": str(ERRORS_MD.name), "results": results}


def main(argv: list[str] | None = None) -> int:
    _cli.setup_stdout()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    _cli.add_version(ap, "explain_error")
    ap.add_argument("query", nargs="*", help="error code(s) or text to search")
    ap.add_argument("--from-response", metavar="FILE", help="inquiry response JSON to scan for codes")
    ap.add_argument("--list", action="store_true", help="list all known codes")
    ap.add_argument("--errors-md", default=str(ERRORS_MD), help=argparse.SUPPRESS)
    args = ap.parse_args(argv)

    rows = load_table(Path(args.errors_md))
    fields = load_field_numbers(Path(args.errors_md))
    aliases = load_aliases(Path(args.errors_md))
    if args.list:
        out = {"count": len(rows), "codes": [{"code": r["code"], "meaning_en": r["meaning_en"]} for r in rows]}
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0

    queries = list(args.query)
    if args.from_response:
        data = json.loads(Path(args.from_response).read_text(encoding="utf-8"))
        queries += codes_from_response(data)
    if not queries:
        ap.error("give an error code, search text, --from-response FILE or --list")

    out = explain(queries, rows, fields, aliases)
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0 if all(r["found"] for r in out["results"]) else 1


if __name__ == "__main__":
    sys.exit(main())
