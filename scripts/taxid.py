#!/usr/bin/env python3
"""Generate, validate and decode the 22-character Moadian taxid
(شماره منحصر به فرد مالیاتی). Offline, stdlib only.

    python scripts/taxid.py generate --memory-id A11216 --date 2023-05-01T00:00:00Z --serial 1
    python scripts/taxid.py generate --memory-id A11216 --indatim 1682899200000 --serial 0x1
    python scripts/taxid.py validate A1121604C1600000000019
    python scripts/taxid.py validate A1121604C1600000000019 --indatim 1682899200000 --inno 0000000001

Algorithm (RC_DCPS.SN_V1.3 §3-1 and Appendix 1; official Java/.NET SDK):
  taxid = MEMORY_ID(6) + hex(days since 1970-01-01, 5) + hex(serial, 10) + check(1)
  check = Verhoeff( toDecimal(MEMORY_ID) + pad(days, 6) + pad(serial, 12) )
  toDecimal: digit -> itself, letter -> its code point (A -> "65").

Note: moadian-full 0.0.2 computes the check digit differently (base36 over the
hex string) and fails every official example, so this script does not use it.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone

DAY_MS = 86_400_000
MAX_SERIAL = 16**10 - 1

# Verhoeff tables (identical in the official Java/.NET SDKs)
_D = [
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9], [1, 2, 3, 4, 0, 6, 7, 8, 9, 5],
    [2, 3, 4, 0, 1, 7, 8, 9, 5, 6], [3, 4, 0, 1, 2, 8, 9, 5, 6, 7],
    [4, 0, 1, 2, 3, 9, 5, 6, 7, 8], [5, 9, 8, 7, 6, 0, 4, 3, 2, 1],
    [6, 5, 9, 8, 7, 1, 0, 4, 3, 2], [7, 6, 5, 9, 8, 2, 1, 0, 4, 3],
    [8, 7, 6, 5, 9, 3, 2, 1, 0, 4], [9, 8, 7, 6, 5, 4, 3, 2, 1, 0],
]
_P = [
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9], [1, 5, 7, 6, 2, 8, 3, 0, 9, 4],
    [5, 8, 0, 3, 7, 9, 6, 1, 4, 2], [8, 9, 1, 6, 0, 4, 3, 5, 2, 7],
    [9, 4, 5, 3, 1, 2, 6, 8, 7, 0], [4, 2, 8, 6, 5, 7, 3, 9, 0, 1],
    [2, 7, 9, 3, 8, 0, 6, 4, 1, 5], [7, 0, 4, 6, 9, 1, 3, 2, 5, 8],
]
_INV = [0, 4, 3, 2, 1, 5, 6, 7, 8, 9]

# RC_DCPS.SN_V1.3 p.6: allowed 1-9 and A D E F G H K M N O P R T W X Y Z;
# forbidden I J L Q V and 0; B C S U reserved.
MEMORY_ID_RE = re.compile(r"^[1-9ADEFGHKMNOPRTWXYZ]{6}$")
TAXID_RE = re.compile(r"^[0-9A-Z]{6}[0-9A-F]{5}[0-9A-F]{10}[0-9]$")


def verhoeff_check_digit(number: str) -> int:
    c = 0
    for i, ch in enumerate(reversed(number)):
        c = _D[c][_P[(i + 1) % 8][int(ch)]]
    return _INV[c]


def verhoeff_is_valid(number_with_check: str) -> bool:
    c = 0
    for i, ch in enumerate(reversed(number_with_check)):
        c = _D[c][_P[i % 8][int(ch)]]
    return c == 0


def to_decimal(memory_id: str) -> str:
    return "".join(ch if ch.isdigit() else str(ord(ch)) for ch in memory_id.upper())


def control_string(memory_id: str, days: int, serial: int) -> str:
    return f"{to_decimal(memory_id)}{days:06d}{serial:012d}"


def days_from_ms(indatim_ms: int) -> int:
    return int(indatim_ms) // DAY_MS


def generate(memory_id: str, indatim_ms: int, serial: int) -> str:
    memory_id = memory_id.upper()
    if len(memory_id) != 6:
        raise ValueError(f"memory id must be 6 characters, got {len(memory_id)}")
    if not 0 <= serial <= MAX_SERIAL:
        raise ValueError("serial must fit in 10 hex digits (0..0xFFFFFFFFFF)")
    days = days_from_ms(indatim_ms)
    if not 0 <= days <= 0xFFFFF:
        raise ValueError("date out of range")
    check = verhoeff_check_digit(control_string(memory_id, days, serial))
    return f"{memory_id}{days:05X}{serial:010X}{check}"


def decode(taxid: str) -> dict:
    t = taxid.strip().upper()
    out: dict = {"taxid": t}
    if len(t) != 22:
        out["error"] = f"length is {len(t)}, must be 22"
        return out
    mem, days_hex, serial_hex, check = t[:6], t[6:11], t[11:21], t[21]
    out.update(memory_id=mem, days_hex=days_hex, serial_hex=serial_hex, check_digit=check)
    try:
        days, serial = int(days_hex, 16), int(serial_hex, 16)
    except ValueError:
        out["error"] = "date or serial part is not hexadecimal"
        return out
    out["days_since_epoch"] = days
    out["date_utc"] = datetime.fromtimestamp(days * 86400, tz=timezone.utc).date().isoformat()
    out["serial"] = serial
    out["inno_expected"] = serial_hex
    return out


def validate(taxid: str, indatim_ms: int | None = None, inno: str | None = None) -> dict:
    info = decode(taxid)
    errors, warnings = [], []
    if "error" in info:
        errors.append(info.pop("error"))
        return {"ok": False, "errors": errors, "warnings": warnings, **info}
    t = info["taxid"]
    if not TAXID_RE.match(t):
        errors.append("taxid must be 6 [0-9A-Z] + 15 hex characters + 1 digit")
    if not MEMORY_ID_RE.match(info["memory_id"]):
        warnings.append(
            "memory id uses characters outside the RC_DCPS.SN_V1.3 alphabet "
            "(allowed 1-9 ADEFGHKMNOPRTWXYZ; 0 I J L Q V forbidden; B C S U reserved)"
        )
    if t[21].isdigit() and not errors:
        expected = verhoeff_check_digit(control_string(info["memory_id"], info["days_since_epoch"], info["serial"]))
        info["check_digit_expected"] = str(expected)
        if str(expected) != t[21]:
            errors.append(f"check digit is {t[21]}, expected {expected}")
    elif not t[21].isdigit():
        errors.append("check digit must be a digit 0-9")
    if indatim_ms is not None and "days_since_epoch" in info:
        d = days_from_ms(indatim_ms)
        if d != info["days_since_epoch"]:
            errors.append(f"date part is day {info['days_since_epoch']} but indatim is day {d} (UTC)")
    if inno is not None and "serial_hex" in info:
        if str(inno).upper() != info["serial_hex"]:
            warnings.append(
                f"inno {inno!r} differs from the taxid serial {info['serial_hex']!r}; "
                "official SDK samples set inno to the 10-char hex serial [UNVERIFIED rule]"
            )
    return {"ok": not errors, "errors": errors, "warnings": warnings, **info}


def _parse_serial(text: str) -> int:
    text = text.strip()
    return int(text, 16) if text.lower().startswith("0x") else int(text)


def _parse_date(text: str) -> int:
    dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        raise ValueError("give a timezone, e.g. 2023-05-01T10:00:00+03:30 or ...Z")
    return int(dt.timestamp() * 1000)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    g = sub.add_parser("generate", help="build a taxid")
    g.add_argument("--memory-id", required=True)
    when = g.add_mutually_exclusive_group(required=True)
    when.add_argument("--indatim", type=int, help="invoice time in epoch milliseconds")
    when.add_argument("--date", help="ISO datetime with timezone")
    g.add_argument("--serial", required=True, help="decimal, or hex with 0x prefix")
    v = sub.add_parser("validate", help="check a taxid")
    v.add_argument("taxid")
    v.add_argument("--indatim", type=int)
    v.add_argument("--inno")
    d = sub.add_parser("decode", help="split a taxid into its parts")
    d.add_argument("taxid")
    args = ap.parse_args(argv)

    try:
        if args.cmd == "generate":
            ms = args.indatim if args.indatim is not None else _parse_date(args.date)
            serial = _parse_serial(args.serial)
            taxid = generate(args.memory_id, ms, serial)
            out = {"taxid": taxid, "inno": taxid[11:21], "indatim": ms,
                   "control_string": control_string(args.memory_id, days_from_ms(ms), serial)}
        elif args.cmd == "validate":
            out = validate(args.taxid, args.indatim, args.inno)
        else:
            out = decode(args.taxid)
    except ValueError as exc:
        out = {"ok": False, "errors": [str(exc)]}
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0 if out.get("ok", "error" not in out) else 1


if __name__ == "__main__":
    sys.exit(main())
