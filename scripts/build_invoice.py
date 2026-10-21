#!/usr/bin/env python3
"""Build a Moadian invoice JSON from a simple YAML/JSON description.

    python scripts/build_invoice.py examples/build-input.yaml -o invoice.json
    python scripts/build_invoice.py input.json --serial 0x1A2B -o invoice.json

Thin wrapper over moadian-full's InvoiceBuilder (loaded offline, see _moadian.py):
the library produces the JSON skeleton and serial; this script then corrects the
fields where moadian-full 0.0.2 disagrees with the official documents, lists every
correction in the report, and runs validate_invoice.py on the result.
No network access, no signing, no sending.

Input (keys in English or the raw JSON codes; amounts in rial):

    memory_id: A11216            # شناسه یکتای حافظه مالیاتی (6 chars)
    seller_tin: "10101234565"    # tins
    date: 1405-02-01             # Jalali or Gregorian; date-only = 12:00 Tehran. Or indatim: <ms>
    type: 1                      # inty  1/2/3
    pattern: 1                   # inp
    subject: 1                   # ins   1 original, 2 correction, 3 cancel, 4 return
    reference_taxid: ...         # irtaxid, for subject 2/3/4
    serial: 26                   # optional; otherwise moadian-full's SerialManager picks one
    settlement: 1                # setm  1 cash, 2 credit, 3 mixed
    cash_amount: ...             # cap   (setm 3 only; excludes VAT)
    buyer: {type: 2, tin: "14011576540", national_id: ..., postal_code: ...}
    items:
      - {sstid: "2330004219206", description: پرینتر, quantity: 2, unit_price: 120000000,
         discount: 4000000, vat_rate: 10, unit: "1627"}
    extra_header: {sbc: "0001"}  # any other header code, passed through
    payments: [{pmt: 4, pv: 1000}]  # raw payment codes, passed through
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _mini_yaml  # noqa: E402
import _moadian  # noqa: E402
import taxid as taxid_mod  # noqa: E402
import validate_invoice  # noqa: E402

TEHRAN = timezone(timedelta(hours=3, minutes=30))  # Iran has used fixed +03:30 since 1401/2022
ITEM_KEYS = {"description": "sstt", "quantity": "am", "unit_price": "fee", "discount": "dis", "vat_rate": "vra",
             "unit": "mu"}
BUYER_KEYS = {"type": "tob", "tin": "tinb", "national_id": "bid", "postal_code": "bpc", "branch": "bbc",
              "passport": "bpn"}


BODY_WHY = {
    "dis": "dis is the line's total discount; moadian-full multiplies it by am (S1 §7-39)",
    "vop": "vop is the VAT share of the cash payment, only meaningful with setm=3 (S1 §7-49)",
    "prdis": "prdis = am × fee, truncated (S1 §7-38)",
    "sstt": "no description given; an empty string fails the format check, so it is left out (sstt is optional)",
    "mu": "no unit given; moadian-full silently inserts \"164\", which is not a verified RC_UMGS code (mu is optional)",
}
HEADER_WHY = {
    "cap": "cap is the cash amount excluding VAT; only mandatory for setm=3 (S1 §7-23)",
    "insp": "insp is the CREDIT amount excluding VAT; only mandatory for setm=3 (S1 §7-24)",
    "tvop": "tvop = Σ vop, only meaningful with setm=3 (S1 §7-25)",
    "setm": "settlement method as given (S1 §7-22)",
}


# ------------------------------------------------------------- dates ----
_BREAKS = [-61, 9, 38, 199, 426, 686, 756, 818, 1111, 1181, 1210, 1635, 2060, 2097, 2192, 2262, 2324, 2394,
           2456, 3178]


def jalali_to_gregorian(jy: int, jm: int, jd: int) -> date:
    """Jalali → Gregorian (algorithm of the jalaali-js library, 33-year leap breaks)."""
    if not (_BREAKS[0] <= jy < _BREAKS[-1]) or not (1 <= jm <= 12) or not (1 <= jd <= 31):
        raise ValueError(f"invalid Jalali date {jy}/{jm}/{jd}")
    gy, leap_j, jp, jump = jy + 621, -14, _BREAKS[0], 0
    for jm_break in _BREAKS[1:]:
        jump = jm_break - jp
        if jy < jm_break:
            break
        leap_j += jump // 33 * 8 + (jump % 33) // 4
        jp = jm_break
    n = jy - jp
    leap_j += n // 33 * 8 + ((n % 33) + 3) // 4
    if jump % 33 == 4 and jump - n == 4:
        leap_j += 1
    leap_g = gy // 4 - ((gy // 100 + 1) * 3) // 4 - 150
    march = 20 + leap_j - leap_g
    offset = (jm - 1) * 31 - (jm // 7) * (jm - 7) + jd - 1
    return date(gy, 3, march) + timedelta(days=offset)


def parse_when(spec: dict) -> datetime:
    if spec.get("indatim") is not None:
        return datetime.fromtimestamp(int(spec["indatim"]) / 1000, tz=timezone.utc)
    text = str(spec.get("date") or "").strip().translate(str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789"))
    if not text:
        raise ValueError("give 'date' (Jalali or Gregorian) or 'indatim' (epoch ms)")
    day, _, clock = text.replace("/", "-").partition("T")
    y, m, d = (int(x) for x in day.split("-"))
    g = jalali_to_gregorian(y, m, d) if y < 1700 else date(y, m, d)
    if not clock:
        return datetime(g.year, g.month, g.day, 12, 0, tzinfo=TEHRAN)
    t = datetime.fromisoformat(f"{g.isoformat()}T{clock.replace('Z', '+00:00')}")
    return t if t.tzinfo else t.replace(tzinfo=TEHRAN)


# ------------------------------------------------------------- build ----
class _FixedSerial:
    def __init__(self, serial: int) -> None:
        self.serial = serial

    def get_next(self) -> int:
        return self.serial


def _items(spec: dict) -> list[dict]:
    out = []
    for raw in spec.get("items") or []:
        item = {ITEM_KEYS.get(k, k): v for k, v in raw.items()}
        for k in ("sstid", "mu"):
            if k in item and item[k] is not None:
                item[k] = str(item[k])
        out.append(item)
    return out


def _trunc(x: Decimal) -> int:
    return int(x)  # positive amounts: int() truncates, as S1 general rule 1 requires


def build(spec: dict, serial: int | None = None, state_dir: str | None = None) -> dict:
    lib = _moadian.load()
    memory_id = str(spec["memory_id"]).upper()
    seller = str(spec.get("seller_tin") or spec.get("tins"))
    when = parse_when(spec)
    inty = int(spec.get("type", spec.get("inty", 1)))
    inp = int(spec.get("pattern", spec.get("inp", 1)))
    ins = int(spec.get("subject", spec.get("ins", 1)))
    setm = int(spec.get("settlement", spec.get("setm", 1)))
    buyer = {BUYER_KEYS.get(k, k): (str(v) if k != "type" and v is not None else v)
             for k, v in (spec.get("buyer") or {}).items()}
    items = _items(spec)
    serial = serial if serial is not None else spec.get("serial")
    if isinstance(serial, str):
        serial = int(serial, 16) if serial.lower().startswith("0x") else int(serial)

    state = Path(state_dir or Path.home() / ".moadian-invoice")
    state.mkdir(parents=True, exist_ok=True)
    builder = lib.InvoiceBuilder(memory_id, seller, storage_path=str(state))
    if serial is not None:
        builder.serial_manager = _FixedSerial(int(serial))
    builder.set_invoice_type(inty, inp)
    builder.set_payment_method(setm)
    builder.set_invoice_time(when)
    if spec.get("reference_taxid") or spec.get("irtaxid"):
        builder.set_correction(spec.get("reference_taxid") or spec.get("irtaxid"))
    # moadian-full insists on an 11/14-digit buyer TIN; feed a placeholder and fix it below
    builder.set_buyer(buyer.get("tinb") or "0" * 11, buyer.get("tob") or 1)
    lib_items = items or [{"sstid": "0" * 13, "sstt": "", "fee": 0}]
    for it in lib_items:
        known = {k: it[k] for k in ("sstid", "sstt", "fee", "am", "mu", "vra") if k in it}
        known["dis"] = int(it.get("dis", 0))  # the library multiplies this by am; corrected below
        builder.add_item(lib.InvoiceItem(**{"sstt": "", **known}))
    inv = builder.build_dict()
    h = inv["header"]
    fixes: list[dict] = []

    def fix(path, old, new, why):
        if old != new:
            fixes.append({"path": path, "moadian_full": old, "corrected": new, "why": why})

    # taxid: moadian-full 0.0.2 fails every official example (references/workflow.md)
    used_serial = int(h["inno"], 16)
    good = taxid_mod.generate(memory_id, h["indatim"], used_serial)
    fix("header.taxid", h["taxid"], good, "official check digit (RC_DCPS.SN_V1.3); library digit is wrong")
    h["taxid"] = good
    fix("header.ins", h["ins"], ins, "library hard-codes ins=1")
    h["ins"] = ins
    fix("header.indati2m", h["indati2m"], None, "only for Articles 9/12 invoices (S1 §7-3)")
    h["indati2m"] = None
    for k in ("tob", "tinb", "bid", "bpc", "bbc", "bpn"):
        new = buyer.get(k)
        if ins in (2, 3, 4) or (inty in (2, 3) and not buyer):
            new = None  # buyer fields are out of pattern for referring invoices (S1 §7-8 rule 3)
        fix(f"header.{k}", h.get(k), new, "buyer data as given (official tob: 1 natural, 2 legal, 3 partnership, 4 foreign)")
        h[k] = new

    # body: recompute with Decimal + truncation and the real line discount (S1 §7-38…§7-51)
    for i, (line, it) in enumerate(zip(inv["body"], items)):
        am, fee = Decimal(str(it.get("am", 1))), Decimal(str(it["fee"]))
        vra, dis = Decimal(str(it.get("vra", 10))), Decimal(str(it.get("dis", 0)))
        prdis = _trunc(am * fee)
        adis = prdis - _trunc(dis)
        vam = _trunc(Decimal(adis) * vra / 100)
        odam, olam = int(it.get("odam") or 0), int(it.get("olam") or 0)
        new = {"prdis": prdis, "dis": _trunc(dis), "adis": adis, "vam": vam, "tsstam": adis + vam + odam + olam,
               "vop": None, "am": it.get("am", 1), "vra": it.get("vra", 10), "mu": it.get("mu"),
               "sstt": it.get("sstt") or None}
        for k, v in new.items():
            fix(f"body[{i}].{k}", line.get(k), v, BODY_WHY.get(k, "follows from the corrected discount (S1 §7-40…§7-51)"))
            line[k] = v
        for k, v in it.items():  # pass through any other raw body codes (odt, odr, odam, cfee, ...)
            if k not in new and k not in ("sstid", "fee"):
                line[k] = v
    if not items:
        inv["body"] = []

    sums = {k: sum(int(b[k] or 0) for b in inv["body"]) for k in ("prdis", "dis", "adis", "vam", "tsstam")}
    todam = sum(int(b.get("odam") or 0) + int(b.get("olam") or 0) for b in inv["body"])
    header_new = {"tprdis": sums["prdis"], "tdis": sums["dis"], "tadis": sums["adis"], "tvam": sums["vam"],
                  "todam": todam, "tbill": sums["tsstam"], "tvop": None, "cap": None, "insp": None, "setm": setm}
    if setm == 3:
        cap = int(spec.get("cash_amount", spec.get("cap", 0)))
        header_new.update(cap=cap, insp=sums["tsstam"] - sums["vam"] - todam - cap)
        if sums["adis"]:  # vop = vam × cap / tadis, truncated (S1 §7-49); tvop = Σ vop (§7-25)
            for b in inv["body"]:
                b["vop"] = _trunc(Decimal(b["vam"]) * cap / sums["adis"])
            header_new["tvop"] = sum(b["vop"] for b in inv["body"])
    if ins == 3:
        header_new = {k: None for k in header_new}  # cancellation: amounts come from the reference
    for k, v in header_new.items():
        fix(f"header.{k}", h.get(k), v, HEADER_WHY.get(k, "header total = Σ body (S1 §7-13…§7-18)"))
        h[k] = v
    if inty in (2, 3) or ins == 3:
        h["setm"] = None if inty == 2 or ins == 3 else h["setm"]
    for k, v in (spec.get("extra_header") or {}).items():
        h[k] = v
    inv["payments"] = [dict(p) for p in spec.get("payments") or []]  # raw codes, passed through
    return {"invoice": inv, "corrections": fixes, "taxid": h["taxid"], "inno": h["inno"],
            "indatim": h["indatim"], "moadian_full_version": lib.version}


def load_input(path: str) -> dict:
    text = sys.stdin.read() if path == "-" else Path(path).read_text(encoding="utf-8")
    if path.endswith(".json") or text.lstrip().startswith("{"):
        return json.loads(text)
    return _mini_yaml.loads(text)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("input", help="YAML or JSON description (or - for stdin)")
    ap.add_argument("-o", "--output", help="write the invoice JSON here (default: print only)")
    ap.add_argument("--serial", help="invoice serial (decimal, or 0x-prefixed hex); overrides the input file")
    ap.add_argument("--state-dir", help="where moadian-full keeps serial history (default ~/.moadian-invoice)")
    args = ap.parse_args(argv)
    try:
        spec = load_input(args.input)
        serial = None
        if args.serial:
            serial = int(args.serial, 16) if args.serial.lower().startswith("0x") else int(args.serial)
        result = build(spec, serial, args.state_dir)
    except (ValueError, KeyError, TypeError, _moadian.MoadianFullMissing) as exc:
        print(json.dumps({"ok": False, "error": f"{type(exc).__name__}: {exc}"}, ensure_ascii=False, indent=2))
        return 2
    check = validate_invoice.validate(result["invoice"])
    report = {"ok": check["ok"], "taxid": result["taxid"], "inno": result["inno"], "indatim": result["indatim"],
              "output": args.output, "corrections_to_moadian_full": result["corrections"],
              "validation": {k: check[k] for k in ("ok", "error_count", "warning_count", "errors", "warnings")}}
    if args.output:
        Path(args.output).write_text(json.dumps(result["invoice"], ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    else:
        report["invoice"] = result["invoice"]
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if check["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
