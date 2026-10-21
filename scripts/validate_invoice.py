#!/usr/bin/env python3
"""Validate a Moadian e-invoice JSON offline (no network, no LLM).

    python scripts/validate_invoice.py invoice.json
    python scripts/validate_invoice.py invoice.json --now 1745222400000   # also check indatim window
    python scripts/validate_invoice.py invoice.json --text                # human-readable

Checks, in order: structure → field types/lengths → enums → required fields for the
type (inty) and pattern (inp) → conditional rules → arithmetic → taxid.
Rules cite RC_IITP.IS_V7.8 ("S1", see references/fields.md) by section; rules that
come only from secondary sources say so. Exit code 0 = no errors (warnings allowed).
"""

from __future__ import annotations

import argparse
import json
import sys
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _ids  # noqa: E402
import _spec as spec  # noqa: E402
import taxid as taxid_mod  # noqa: E402
from _arith import check_arithmetic  # noqa: E402
from _common import FIELD_NO, Report, _plain, code_hint, num  # noqa: E402

SECTIONS = ("header", "body", "payments")


# ---------------------------------------------------------------- types ----
def check_type(rep: Report, path: str, field: str, value) -> None:
    code = spec.FIELDS[field][1]
    if code == "?" or value is None:
        return
    kind, rest = code[0], code[1:]
    src = "S1 §7 field table"
    if kind in "SN":
        if not isinstance(value, str):
            rep.error(path, f"{field} must be a JSON string", "type", src, actual=type(value).__name__,
                      code=code_hint(field, "1", "03"))
            return
        if kind == "N" and not value.isdigit():
            rep.error(path, f"{field} must contain digits 0-9 only", "regex", src, actual=value,
                      code=code_hint(field, "1", "04"))
            return
        n = len(value)
        if rest.startswith("<="):
            ok = 1 <= n <= int(rest[2:])
        elif "-" in rest:
            lo, hi = map(int, rest.split("-"))
            ok = lo <= n <= hi
        else:
            ok = n in {int(x) for x in rest.split("|")}
        if not ok:
            rep.error(path, f"{field} length {n} not allowed ({code})", "length", src, expected=code,
                      actual=value, code=code_hint(field, "1", "04"))
    elif kind == "I":
        if not isinstance(value, int) or isinstance(value, bool):
            rep.error(path, f"{field} must be an integer", "type", src, actual=value, code=code_hint(field, "1", "03"))
        elif len(str(abs(value))) > int(rest[2:]):
            rep.error(path, f"{field} has more than {rest[2:]} digits", "length", src, actual=value,
                      code=code_hint(field, "1", "04"))
    elif kind == "D":
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            rep.error(path, f"{field} must be a JSON number", "type", src, actual=value, code=code_hint(field, "1", "03"))
            return
        int_digits, frac_digits = map(int, rest.split(","))
        d = Decimal(str(value))
        sign, digits, exp = d.as_tuple()
        frac = max(0, -exp)
        if frac > frac_digits and d != d.to_integral_value():
            rep.error(path, f"{field} allows {frac_digits} decimal places (truncate, do not round)", "decimals",
                      "S1 §7 field table; general rule 1", actual=value, code=code_hint(field, "1", "09"))
        if len(str(int(abs(d)))) > int_digits:
            rep.error(path, f"{field} has more than {int_digits} integer digits", "length", src, actual=value)
        if d < 0:
            rep.error(path, f"{field} must not be negative", "range", src, actual=value, code=code_hint(field, "1", "06"))


# ---------------------------------------------------------- structure ----
def check_structure(rep: Report, inv) -> bool:
    if not isinstance(inv, dict):
        rep.error("$", "invoice must be a JSON object with header, body, payments", "structure", "S1 Table 2")
        return False
    if not isinstance(inv.get("header"), dict):
        rep.error("header", "header object is missing", "structure", "S1 Table 2")
        return False
    if not isinstance(inv.get("body", []), list):
        rep.error("body", "body must be a list of items", "structure", "S1 Table 2")
        return False
    if inv.get("payments") is not None and not isinstance(inv["payments"], list):
        rep.error("payments", "payments must be a list", "structure", "S1 Table 2")
        return False
    for key in inv:
        if key not in ("header", "body", "payments", "extension"):
            rep.warn(key, f"unexpected top-level key {key!r}", "structure", "S1 Table 2")
    return True


def iter_fields(inv):
    """Yield (section, path, field, value, owner_dict)."""
    for f, v in inv["header"].items():
        yield "header", f"header.{f}", f, v
    for sec in ("body", "payments"):
        for i, row in enumerate(inv.get(sec) or []):
            if not isinstance(row, dict):
                yield sec, f"{sec}[{i}]", None, row
                continue
            for f, v in row.items():
                yield sec, f"{sec}[{i}].{f}", f, v


def check_fields(rep: Report, inv) -> None:
    for sec, path, field, value in iter_fields(inv):
        if field is None:
            rep.error(path, f"each {sec} entry must be an object", "structure", "S1 Table 2")
            continue
        if field not in spec.FIELDS:
            rep.warn(path, f"unknown field {field!r} (not in RC_IITP.IS_V7.8); the system rejects disallowed "
                     "properties with a T=1/D=01 code", "unknown-field", "S1 Table 2; errors.md §2")
            continue
        home = spec.FIELDS[field][0]
        if home != sec:
            rep.error(path, f"{field} belongs in {home}, not {sec}", "placement", "S1 Table 2")
            continue
        check_type(rep, path, field, value)


# --------------------------------------------------------------- enums ----
def check_enums(rep: Report, h: dict, inv) -> tuple[int | None, int | None, int | None]:
    inty, inp, ins = h.get("inty"), h.get("inp"), h.get("ins")
    for field, value, path in [(f, h.get(f), f"header.{f}") for f in ("inty", "inp", "ins", "tob", "setm", "ft", "lt")] + [
        ("pmt", p.get("pmt"), f"payments[{i}].pmt") for i, p in enumerate(inv.get("payments") or []) if isinstance(p, dict)
    ]:
        if isinstance(value, int) and not isinstance(value, bool) and value not in spec.ENUMS[field]:
            rep.error(path, f"{field}={value} is not an allowed value {sorted(spec.ENUMS[field])}", "enum",
                      "S1 §3, §7", actual=value, code=code_hint(field, "1", "02"))
    if inty in spec.PATTERNS_BY_TYPE and isinstance(inp, int) and inp in spec.ENUMS["inp"] \
            and inp not in spec.PATTERNS_BY_TYPE[inty]:
        rep.error("header.inp", f"pattern inp={inp} is not allowed for invoice type inty={inty}", "type-pattern",
                  "S1 §7-7", expected=list(spec.PATTERNS_BY_TYPE[inty]), actual=inp)
    if ins == 4 and inp in spec.NO_RETURN_PATTERNS:
        rep.error("header.ins", f"sales return (ins=4) is not allowed for pattern inp={inp}", "subject", "S1 §7-8")
    ok = lambda v, f: v if (isinstance(v, int) and v in spec.ENUMS[f]) else None  # noqa: E731
    return ok(inty, "inty"), ok(inp, "inp"), ok(ins, "ins")


# ------------------------------------------------------------ required ----
def check_required(rep: Report, inv, inty, inp, ins) -> None:
    h, body = inv["header"], inv.get("body") or []
    if inty == 3:
        rep.notes.append("inty=3 has no column in S1 Table 1: only basic header fields and the payment fields "
                         "that §7-52…§7-59 make mandatory for type 3 were checked [UNVERIFIED coverage].")
        for f in ("taxid", "indatim", "inty", "inp", "ins", "tins", "tvam", "tbill"):
            if h.get(f) is None:
                rep.error(f"header.{f}", f"{f} is missing", "required", "S1 Table 1", code=code_hint(f, "0"))
        pays = [p for p in inv.get("payments") or [] if isinstance(p, dict)]
        if not pays:
            rep.error("payments", "type 3 invoices need payment data", "required", "S1 §7-52…§7-60")
        for i, p in enumerate(pays):
            for f in spec.INTY3_REQUIRED_PAYMENT:
                if p.get(f) is None:
                    rep.error(f"payments[{i}].{f}", f"{f} is mandatory for inty=3", "required", "S1 §7-52…§7-59")
        return
    if (inty, inp) not in spec.MATRIX_COLUMNS:
        return
    referring = ins in (2, 3, 4)
    for field, (sec, _, fa) in spec.FIELDS.items():
        st = spec.status(field, inty, inp)
        if st is None:
            continue
        rows = [h] if sec == "header" else ([b for b in body if isinstance(b, dict)] if sec == "body" else [])
        for i, row in enumerate(rows):
            path = f"header.{field}" if sec == "header" else f"body[{i}].{field}"
            present = row.get(field) is not None
            if st == "M" and not present:
                if ins == 3 and (sec == "body" or field in ("tprdis", "tadis", "todam", "tvam", "tbill", "setm")):
                    continue  # cancellation takes amounts from the reference invoice (S1 §5, §7-8)
                if referring and field in ("tob", "tinb", "bid", "bpc"):
                    continue  # buyer fields are out of pattern for ins 2/3/4 (S1 §7-8 rule 3)
                rep.error(path, f"{field} ({fa}) is mandatory for inty={inty}, inp={inp}", "required",
                          "S1 Table 1", code=code_hint(field, "0"))
            elif st == "-" and present:
                rep.warn(path, f"{field} is ignored («خارج از الگو») for inty={inty}, inp={inp}; the system may "
                         "answer with a 14xxx out-of-pattern warning", "out-of-pattern", "S1 Table 1; errors.md",
                         code=f"14{FIELD_NO[field]}" if field in FIELD_NO else None)
    if not body and ins != 3:
        rep.error("body", "an invoice needs at least one item", "required", "S1 Table 2; errors.md §2")
    if ins == 3 and body:
        rep.warn("body", "cancellations (ins=3) take items from the reference invoice; secondary sources report "
                 "14xxx warnings when items/totals are sent", "cancellation", "S1 §7-8; errors.md E8")


# --------------------------------------------------------- conditional ----
def check_conditional(rep: Report, inv, inty, inp, ins) -> None:
    h = inv["header"]
    if ins in (2, 3, 4) and h.get("irtaxid") is None:
        rep.error("header.irtaxid", "irtaxid (reference taxid) is mandatory for ins 2/3/4", "conditional",
                  "S1 §7-6", code=code_hint("irtaxid", "0"))
    if ins == 1 and h.get("irtaxid") is not None:
        rep.warn("header.irtaxid", "irtaxid is only used by corrections, cancellations and returns", "conditional", "S1 §7-6")
    if ins in (2, 3, 4):
        for f in ("inty", "inp"):
            if h.get(f) is not None and ins == 3:
                rep.warn(f"header.{f}", f"{f} is ignored on cancellations; secondary sources report warning "
                         f"14{FIELD_NO[f]}", "referring", "S1 §5-3; errors.md E9")
    if isinstance(h.get("irtaxid"), str) and len(h["irtaxid"]) == 22:
        res = taxid_mod.validate(h["irtaxid"])
        for e in res["errors"]:
            rep.error("header.irtaxid", f"reference taxid: {e}", "taxid", "RC_DCPS.SN_V1.3")
    if h.get("indati2m") is not None:
        rep.warn("header.indati2m", "indati2m is only needed for invoices under Articles 9 and 12 of the store "
                 "terminals law; otherwise leave it out (moadian-full fills it by default)", "conditional", "S1 §7-3")
    if inty == 1 and ins == 1 and inp not in (11,):
        tob = h.get("tob")
        if tob in (2, 3) and not h.get("tinb"):
            rep.error("header.tinb", "legal entity / civil partnership buyer (tob 2/3) on a type-1 invoice needs tinb",
                      "buyer", "S1 §7-9 rule 5", code=code_hint("tinb", "0"))
        if tob in (1, 4) and not h.get("tinb") and not (h.get("bid") and h.get("bpc")):
            rep.error("header.tinb", "natural-person / foreign buyer (tob 1/4) on a type-1 invoice needs tinb, "
                      "or bid together with bpc", "buyer", "S1 §7-9 rule 4", code=code_hint("tinb", "0"))
    setm = h.get("setm")
    if setm == 3 and inty == 1:
        for f in ("cap", "insp"):
            if h.get(f) is None:
                rep.error(f"header.{f}", f"{f} is mandatory when setm=3 (cash/credit)", "conditional", "S1 §7-23, §7-24",
                          code=code_hint(f, "0"))
    if setm in (1, 2) and (h.get("cap") is not None or h.get("insp") is not None):
        rep.warn("header.cap", "cap/insp are only required for setm=3; secondary sources report 14029/14030 warnings "
                 "when they are sent otherwise", "conditional", "S1 §7-23; errors.md E2")
        if setm == 1 and (num(h.get("insp")) or 0) > 0:
            rep.warn("header.insp", "insp is the CREDIT (نسیه) amount, but setm=1 says the invoice is cash. "
                     "moadian-full 0.0.2 sets insp=tadis on cash invoices — that is wrong", "settlement", "S1 §7-24")
    vra_zero = inp in spec.ZERO_VAT_PATTERNS
    for i, b in enumerate(inv.get("body") or []):
        if isinstance(b, dict) and vra_zero and (num(b.get("vra")) or 0) != 0:
            rep.error(f"body[{i}].vra", f"vra must be 0 for pattern inp={inp}", "vat", "S1 §7-41", actual=b.get("vra"))
    unchecked = [f for f in ("bid", "bpn", "odt", "odr", "odam", "olt", "olr", "olam", "nw", "tonw", "oci", "dci",
                             "rid", "did", "vba") if spec.status(f, inty or 0, inp or 0) == "C"]
    if unchecked:
        rep.notes.append("conditionally-mandatory fields not machine-checked (read their rules in references/"
                         "fields.md): " + ", ".join(unchecked))


# --------------------------------------------------------------- taxid ----
# ----------------------------------------------------------- id digits ----
ID_SOURCE = "persian-tools npm 4.0.4 / PyPI 0.0.11 (secondary; see scripts/_ids.py)"


def check_ids(rep: Report, inv) -> None:
    """Check digits of national codes / legal-entity ids. Warnings only: the algorithms
    come from open-source libraries, not from an INTA document."""
    h = inv["header"]
    tob = h.get("tob")
    # (path, value, kind, likely code, note)
    targets = [
        ("header.tins", h.get("tins"), "legal", "0300901",
         "if the seller is a legal entity (civil partnerships also use 11 digits; their algorithm is not sourced)"),
        ("header.tinc", h.get("tinc"), "legal", None, ""),
    ]
    if tob != 3:
        targets.append(("header.tinb", h.get("tinb"), "legal", "0301201", "buyer economic code (11 digits = legal entity)"))
    if tob in (1, None):
        targets.append(("header.bid", h.get("bid"), "national", "1301101", ""))
    if tob == 2:
        targets.append(("header.bid", h.get("bid"), "legal", "1301101", ""))
    for f in ("tid", "rid", "did"):
        targets.append((f"header.{f}", h.get(f), "auto", None, ""))
    for i, p in enumerate(inv.get("payments") or []):
        if isinstance(p, dict):
            targets.append((f"payments[{i}].pid", p.get("pid"), "auto", None, ""))
    for path, value, kind, code, note in targets:
        problem = _ids.check(value, kind)
        if problem:
            rep.warn(path, f"{value} {problem}{' — ' + note if note else ''}; the system will likely reject it as "
                     "not matching its records. Double-check the number with the user", "id-check-digit", ID_SOURCE,
                     code=code)


def check_taxid(rep: Report, h: dict) -> None:
    t, indatim, inno = h.get("taxid"), h.get("indatim"), h.get("inno")
    if isinstance(inno, str) and not (len(inno) == 10 and all(c in "0123456789abcdefABCDEF" for c in inno)):
        rep.error("header.inno", "inno must be 10 hexadecimal characters", "regex", "S1 §7-5; errors.md 0100504",
                  actual=inno, code="0100504")
    if not isinstance(t, str) or len(t) != 22:
        return
    res = taxid_mod.validate(t, indatim if isinstance(indatim, int) else None, inno if isinstance(inno, str) else None)
    for e in res["errors"]:
        rep.error("header.taxid", e, "taxid", "RC_DCPS.SN_V1.3; S1 §7-1, §7-2", code="0300101")
    for w in res["warnings"]:
        rep.warn("header.taxid" if "memory" in w else "header.inno", w, "taxid", "RC_DCPS.SN_V1.3; errors.md 1300501",
                 code=None if "memory" in w else "1300501")


def check_dates(rep: Report, h: dict, now_ms: int) -> None:
    ind = h.get("indatim")
    if not isinstance(ind, int):
        return
    if ind > now_ms + 30_000:
        rep.error("header.indatim", "indatim is in the future (system tolerance ~30 s)", "R21", "S1 §7-2; errors.md E1",
                  code="0200201")
    elif now_ms - ind > 7 * 86_400_000:
        rep.warn("header.indatim", "indatim is more than one week old; S1 requires sending within a week "
                 "(secondary sources saw type 1 accepted up to ~13 days)", "R21", "S1 §7-2; errors.md E4", code="0200201")


def validate(inv, now_ms: int | None = None) -> dict:
    rep = Report()
    summary: dict = {}
    if check_structure(rep, inv):
        h = inv["header"]
        check_fields(rep, inv)
        check_ids(rep, inv)
        inty, inp, ins = check_enums(rep, h, inv)
        check_required(rep, inv, inty, inp, ins)
        check_conditional(rep, inv, inty, inp, ins)
        sums = check_arithmetic(rep, inv, inty, inp, ins)
        check_taxid(rep, h)
        if now_ms is not None:
            check_dates(rep, h, now_ms)
        else:
            rep.notes.append("date window not checked (pass --now to check indatim against the current time)")
        summary = {
            "inty": inty, "inty_fa": spec.ENUMS["inty"].get(inty), "inp": inp, "inp_fa": spec.ENUMS["inp"].get(inp),
            "ins": ins, "ins_fa": spec.ENUMS["ins"].get(ins), "lines": len(inv.get("body") or []),
            "body_sums": sums,
        }
    return {"ok": not rep.errors, "error_count": len(rep.errors), "warning_count": len(rep.warnings),
            "summary": summary, "errors": rep.errors, "warnings": rep.warnings, "notes": rep.notes}


def to_text(res: dict) -> str:
    lines = [f"{'OK' if res['ok'] else 'INVALID'}: {res['error_count']} error(s), {res['warning_count']} warning(s)"]
    for kind in ("errors", "warnings"):
        for e in res[kind]:
            extra = f" (expected {e['expected']}, found {e['actual']})" if "expected" in e and "should be" not in e["message"] else ""
            code = f" [{e['code_hint']}]" if e.get("code_hint") else ""
            lines.append(f"  {kind[:-1].upper()} {e['path']}: {e['message']}{extra}{code} — {e['source']}")
    lines += [f"  NOTE {n}" for n in res["notes"]]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("file", help="invoice JSON file, or - for stdin")
    ap.add_argument("--now", type=int, help="current time in epoch ms, to check the indatim window")
    ap.add_argument("--text", action="store_true", help="human-readable output instead of JSON")
    args = ap.parse_args(argv)
    raw = sys.stdin.read() if args.file == "-" else Path(args.file).read_text(encoding="utf-8")
    try:
        inv = json.loads(raw)
    except json.JSONDecodeError as exc:
        res = {"ok": False, "error_count": 1, "warning_count": 0, "summary": {}, "notes": [], "warnings": [],
               "errors": [{"path": "$", "message": f"invalid JSON: {exc}", "rule": "json", "source": "errors.md §2",
                           "code_hint": "0100010"}]}
    else:
        res = validate(inv, args.now)
    print(to_text(res) if args.text else json.dumps(res, ensure_ascii=False, indent=2))
    return 0 if res["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
