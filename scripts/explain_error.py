#!/usr/bin/env python3
"""Explain a Moadian error code using references/errors.md.

Usage:
    python scripts/explain_error.py 0300101
    python scripts/explain_error.py "duplicate"        # search messages
    python scripts/explain_error.py --from-response resp.json
    python scripts/explain_error.py --list

Reads only the local errors.md table (no network). Output is JSON. A code that
is not in the table is reported as unknown; this script never invents meanings.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

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
        row["unverified"] = "[UNVERIFIED]" in line
        rows.append(row)
    return rows


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


def explain(queries: list[str], rows: list[dict]) -> dict:
    results = []
    for q in queries:
        matches = lookup(q, rows)
        results.append({
            "query": q,
            "found": bool(matches),
            "matches": matches,
            "note": None if matches else (
                "Not in references/errors.md. Do not guess a meaning: quote the raw "
                "message from the response and check the current INTA error list."
            ),
        })
    return {"source": str(ERRORS_MD.name), "results": results}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("query", nargs="*", help="error code(s) or text to search")
    ap.add_argument("--from-response", metavar="FILE", help="inquiry response JSON to scan for codes")
    ap.add_argument("--list", action="store_true", help="list all known codes")
    ap.add_argument("--errors-md", default=str(ERRORS_MD), help=argparse.SUPPRESS)
    args = ap.parse_args(argv)

    rows = load_table(Path(args.errors_md))
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

    out = explain(queries, rows)
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0 if all(r["found"] for r in out["results"]) else 1


if __name__ == "__main__":
    sys.exit(main())
