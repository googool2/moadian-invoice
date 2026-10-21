#!/usr/bin/env python3
"""Synthetic benchmark for validate_invoice.py (playbook phase 3).

Builds a corpus in memory and checks the validator against it:
  * TRAPS   — valid but unusual invoices (gold, export, mixed settlement, cancellation, type 2,
              decimals, other taxes, correction, return …). Must give 0 errors and no
              warnings beyond the ones listed.
  * DEFECTS — one seeded mistake each, with the field path and severity the validator must
              report. Must be found at that path, at the root (not as "follows from"), with no
              other unexpected root errors.

Amounts are written out by hand below, not computed with the validator's code, so the
benchmark does not grade the validator against itself. Taxids come from taxid.py, which has
its own official test vectors.

    python bench/bench.py                 # writes bench/RESULTS.md and bench/results.json
    python bench/bench.py --out DIR

Exit code 1 if any trap or defect fails.
"""

from __future__ import annotations

import argparse
import copy
import json
import platform
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "skills" / "moadian-invoice" / "scripts"))
import _cli  # noqa: E402
import taxid  # noqa: E402
import validate_invoice  # noqa: E402

NOW = 1776760200000            # 1405-02-01 12:00 Tehran, the "current time" for date checks
DAY = 86_400_000
SELLER, BUYER = "10101234565", "14011576540"      # legal ids with valid check digits
PERSON, POSTAL = "0012345679", "1234567890"        # national code with a valid check digit


def header(serial: int, indatim: int = NOW - 3_600_000, **fields) -> dict:
    t = taxid.generate("A11216", indatim, serial)
    return {"taxid": t, "indatim": indatim, "inty": 1, "inno": t[11:21], "inp": 1, "ins": 1,
            "tins": SELLER, **fields}


def line(**fields) -> dict:
    return {"sstid": "2330004219206", "sstt": "کالا", "mu": "1627", **fields}


# --------------------------------------------------------------------- traps ----
def traps() -> dict[str, dict]:
    t = {}
    # 1. plain sale, legal buyer, cash: 2 × 120,000,000 − 4,000,000 = 236,000,000; VAT 10 % = 23,600,000
    t["sale-legal-cash"] = {"header": header(1, tob=2, tinb=BUYER, tprdis=240000000, tdis=4000000,
                                             tadis=236000000, tvam=23600000, todam=0, tbill=259600000, setm=1),
                            "body": [line(am=2, fee=120000000, prdis=240000000, dis=4000000, adis=236000000,
                                          vra=10, vam=23600000, tsstam=259600000)], "payments": []}
    # 2. natural person without economic code: bid + bpc (S1 §7-9 rule 4)
    t["sale-natural-person-bid-bpc"] = {"header": header(2, tob=1, bid=PERSON, bpc=POSTAL, tprdis=50000000, tdis=0,
                                                         tadis=50000000, tvam=5000000, todam=0, tbill=55000000, setm=1),
                                        "body": [line(am=1, fee=50000000, prdis=50000000, dis=0, adis=50000000,
                                                      vra=10, vam=5000000, tsstam=55000000)], "payments": []}
    # 3. type 2: no buyer, no setm (ignored for type 2)
    t["type2-no-buyer"] = {"header": header(3, inty=2, tprdis=1000000, tdis=0, tadis=1000000, tvam=100000, todam=0,
                                            tbill=1100000),
                           "body": [line(am=1, fee=1000000, prdis=1000000, dis=0, adis=1000000, vra=10, vam=100000,
                                         tsstam=1100000)], "payments": []}
    # 4. mixed settlement: tadis 10,000,000 = cap 6,000,000 + insp 4,000,000; vop = 1,000,000 × 6/10 = 600,000
    t["setm3-mixed"] = {"header": header(4, tob=2, tinb=BUYER, tprdis=10000000, tdis=0, tadis=10000000, tvam=1000000,
                                         todam=0, tbill=11000000, setm=3, cap=6000000, insp=4000000, tvop=600000),
                        "body": [line(am=1, fee=10000000, prdis=10000000, dis=0, adis=10000000, vra=10, vam=1000000,
                                      vop=600000, tsstam=11000000)], "payments": []}
    # 5. gold (inp 3): tcpbs = 5 + 3 + 2 = 10 M; adis = 100 M + 10 M − 0; vam = 10 % of tcpbs + 10 % of prdis
    t["gold-pattern"] = {"header": header(5, inp=3, tob=2, tinb=BUYER, tprdis=100000000, tdis=0, tadis=110000000,
                                          tvam=11000000, todam=0, tbill=121000000, setm=1),
                         "body": [line(am=1, fee=100000000, prdis=100000000, dis=0, consfee=5000000, spro=3000000,
                                       bros=2000000, tcpbs=10000000, adis=110000000, vra=10, vam=11000000,
                                       tsstam=121000000, cui=750)], "payments": []}
    # 6. export (inp 7): vra 0, tsstam = ssrv + vam, tbill = torv + tvam + todam
    t["export-pattern"] = {"header": header(6, inp=7, tvam=0, todam=0, tbill=500000000, torv=500000000, tocv=10000,
                                            setm=2),
                           "body": [line(am=10, cut="USD", exr=50000, ssrv=500000000, sscv=10000, vra=0, vam=0,
                                         tsstam=500000000)], "payments": []}
    # 7. cancellation: header only, reference taxid (S1 §7-8; header-only per sandbox logs)
    ref = header(1)["taxid"]
    t["cancellation-header-only"] = {"header": {**header(7), "ins": 3, "irtaxid": ref}, "body": [], "payments": []}
    for k in ("inty", "inp"):
        del t["cancellation-header-only"]["header"][k]
    # 8. decimals: 2.5 × 333,333.33 = 833,333.325 → 833,333; 9 % → 74,999.97 → 74,999
    t["decimal-quantity-and-price"] = {"header": header(8, tob=2, tinb=BUYER, tprdis=833333, tdis=0, tadis=833333,
                                                        tvam=74999, todam=0, tbill=908332, setm=1),
                                       "body": [line(am=2.5, fee=333333.33, prdis=833333, dis=0, adis=833333, vra=9,
                                                     vam=74999, tsstam=908332)], "payments": []}
    # 9. other taxes: odr 3 % of 1,000,000 = 30,000; todam = 30,000
    t["other-taxes-odam"] = {"header": header(9, tob=2, tinb=BUYER, tprdis=1000000, tdis=0, tadis=1000000, tvam=100000,
                                              todam=30000, tbill=1130000, setm=1),
                             "body": [line(am=1, fee=1000000, prdis=1000000, dis=0, adis=1000000, vra=10, vam=100000,
                                           odt="عوارض", odr=3, odam=30000, tsstam=1130000)], "payments": []}
    # 10. correction and 11. sales return: irtaxid, no buyer fields, later indatim
    for name, ins, serial in (("correction-ins2", 2, 10), ("sales-return-ins4", 4, 11)):
        t[name] = {"header": header(serial, ins=ins, irtaxid=ref, tprdis=1000000, tdis=0, tadis=1000000, tvam=100000,
                                    todam=0, tbill=1100000, setm=1),
                   "body": [line(am=1, fee=1000000, prdis=1000000, dis=0, adis=1000000, vra=10, vam=100000,
                                 tsstam=1100000)], "payments": []}
    # 12. credit sale with a zero payment line (pv must be 0 for setm 2)
    t["credit-sale-zero-payment"] = {"header": header(12, tob=2, tinb=BUYER, tprdis=2000000, tdis=0, tadis=2000000,
                                                      tvam=200000, todam=0, tbill=2200000, setm=2),
                                     "body": [line(am=4, fee=500000, prdis=2000000, dis=0, adis=2000000, vra=10,
                                                   vam=200000, tsstam=2200000)], "payments": [{"pmt": 1, "pv": 0}]}
    # 13. multi-line with discounts on both lines
    t["multi-line-discounts"] = {"header": header(13, tob=2, tinb=BUYER, tprdis=3500000, tdis=350000, tadis=3150000,
                                                  tvam=315000, todam=0, tbill=3465000, setm=1),
                                 "body": [line(am=3, fee=500000, prdis=1500000, dis=150000, adis=1350000, vra=10,
                                               vam=135000, tsstam=1485000),
                                          line(am=2, fee=1000000, prdis=2000000, dis=200000, adis=1800000, vra=10,
                                               vam=180000, tsstam=1980000)], "payments": []}
    return t


# ------------------------------------------------------------------- defects ----
def defects(t: dict) -> list[dict]:
    """(name, base trap, mutation, expected path, severity, also-allowed root error paths)."""
    def d(name, base, mutate, path, severity="error", also=(), now=None):
        return {"name": name, "base": base, "mutate": mutate, "path": path, "severity": severity,
                "also": set(also), "now": now}

    def set_(sec, **kv):
        def f(inv):
            (inv["header"] if sec == "h" else inv["body"][0]).update(kv)
        return f

    def delete(sec, key):
        def f(inv):
            (inv["header"] if sec == "h" else inv["body"][0]).pop(key)
        return f

    bad_check = t["sale-legal-cash"]["header"]["taxid"]
    bad_check = bad_check[:-1] + str((int(bad_check[-1]) + 1) % 10)
    return [
        d("prdis rounded instead of truncated", "decimal-quantity-and-price", set_("b", prdis=833334), "body[0].prdis"),
        d("adis ≠ prdis − dis", "sale-legal-cash", set_("b", adis=235000000), "body[0].adis"),
        d("vam rounded half-up", "decimal-quantity-and-price", set_("b", vam=75000, tsstam=908333), "body[0].vam"),
        d("dis greater than prdis", "sale-legal-cash",
          lambda inv: (inv["body"][0].update(dis=250000000), inv["header"].update(tdis=250000000)),
          "body[0].dis", also={"body[0].adis"}),
        d("odam ≠ adis × odr", "other-taxes-odam", set_("b", odam=31000), "body[0].odam"),
        d("tsstam ≠ adis + vam + odam", "other-taxes-odam", set_("b", tsstam=1100000), "body[0].tsstam"),
        d("tvam ≠ Σ vam", "multi-line-discounts", set_("h", tvam=300000), "header.tvam"),
        d("tbill ≠ Σ tsstam", "multi-line-discounts", set_("h", tbill=3500000), "header.tbill"),
        d("tdis ≠ Σ dis", "multi-line-discounts", set_("h", tdis=200000), "header.tdis"),
        d("cap = tbill on a cash invoice", "sale-legal-cash", set_("h", cap=259600000), "header.cap"),
        d("setm 3 with cap + insp ≠ net", "setm3-mixed", set_("h", insp=5000000), "header.cap"),
        d("setm 3 without insp", "setm3-mixed", delete("h", "insp"), "header.insp"),
        d("gold tcpbs ≠ consfee + spro + bros", "gold-pattern", set_("b", tcpbs=9000000), "body[0].tcpbs",
          also={"body[0].adis", "body[0].vam"}),
        d("tax17 above tvam", "sale-legal-cash", set_("h", tax17=30000000), "header.tax17"),
        d("pv on a credit invoice", "credit-sale-zero-payment", lambda inv: inv["payments"][0].update(pv=1000),
          "payments[0].pv"),
        d("legal buyer without tinb", "sale-legal-cash", delete("h", "tinb"), "header.tinb"),
        d("natural person without tinb or bpc", "sale-natural-person-bid-bpc", delete("h", "bpc"), "header.tinb"),
        d("inty 4 (does not exist)", "sale-legal-cash", set_("h", inty=4), "header.inty"),
        d("contracting pattern on type 2", "type2-no-buyer", set_("h", inp=4), "header.inp"),
        d("correction without irtaxid", "correction-ins2", delete("h", "irtaxid"), "header.irtaxid"),
        d("return on an export invoice", "export-pattern", set_("h", ins=4, irtaxid=bad_check[:-1] + "0"),
          "header.ins", also={"header.irtaxid"}),
        d("wrong taxid check digit", "sale-legal-cash", set_("h", taxid=bad_check), "header.taxid"),
        d("taxid day ≠ indatim day", "sale-legal-cash",
          lambda inv: inv["header"].update(indatim=inv["header"]["indatim"] - DAY), "header.taxid"),
        d("inno not 10 hex characters", "sale-legal-cash", set_("h", inno="12"), "header.inno"),
        d("sstid with 12 digits", "sale-legal-cash", set_("b", sstid="233000421920"), "body[0].sstid"),
        d("tins sent as a number", "sale-legal-cash", set_("h", tins=10101234565), "header.tins"),
        d("vam with decimals", "sale-legal-cash", set_("b", vam=23600000.5), "body[0].vam", also={"body[0].tsstam"}),
        d("body field in the header", "sale-legal-cash", set_("h", vam=1), "header.vam"),
        d("VAT on a chain-sale pattern (inp 14)", "sale-legal-cash", set_("h", inp=14), "body[0].vra"),
        d("required fee missing", "sale-legal-cash", delete("b", "fee"), "body[0].fee"),
        d("type 3 without payment data", "sale-legal-cash", set_("h", inty=3), "payments"),
        d("indatim in the future", "sale-legal-cash", lambda inv: None, "header.indatim", now=NOW - 3 * 3_600_000),
        d("seller legal id check digit", "sale-legal-cash", set_("h", tins="10101234567"), "header.tins", "warning"),
        d("buyer national code check digit", "sale-natural-person-bid-bpc", set_("h", bid="0012345678"), "header.bid",
          "warning"),
        d("field ignored for the pattern", "sale-legal-cash", set_("h", billid="123456"), "header.billid", "warning"),
        d("unknown field", "sale-legal-cash", set_("h", foo=1), "header.foo", "warning"),
        d("items sent on a cancellation", "cancellation-header-only",
          lambda inv: inv["body"].append(copy.deepcopy(t["sale-legal-cash"]["body"][0])), "body", "warning"),
    ]


def is_root(issue: dict) -> bool:
    m = issue["message"]
    return "follows from" not in m and "corrected body" not in m


def run(out_dir: Path) -> dict:
    started = time.perf_counter()
    corpus = traps()
    results = {"traps": [], "defects": []}
    for name, inv in corpus.items():
        res = validate_invoice.validate(copy.deepcopy(inv), NOW)
        ok = res["ok"] and not res["warnings"]
        results["traps"].append({"name": name, "pass": ok, "errors": [e["path"] + ": " + e["message"] for e in res["errors"]],
                                 "warnings": [w["path"] + ": " + w["message"] for w in res["warnings"]]})
    for spec in defects(corpus):
        inv = copy.deepcopy(corpus[spec["base"]])
        spec["mutate"](inv)
        res = validate_invoice.validate(inv, spec["now"] if spec["now"] is not None else NOW)
        pool = res["errors"] if spec["severity"] == "error" else res["warnings"]
        hit = [i for i in pool if i["path"] == spec["path"] and is_root(i)]
        extra = sorted({e["path"] for e in res["errors"] if is_root(e) and e["path"] != spec["path"]} - spec["also"])
        if spec["severity"] == "warning":
            extra = sorted({e["path"] for e in res["errors"]})  # a warning-only defect must not cause errors
        results["defects"].append({"name": spec["name"], "expected": f"{spec['severity']} at {spec['path']}",
                                   "found": bool(hit), "unexpected_root_errors": extra,
                                   "code_hint": hit[0].get("code_hint") if hit else None,
                                   "pass": bool(hit) and not extra})
    tp = sum(r["pass"] for r in results["traps"])
    dp = sum(r["pass"] for r in results["defects"])
    results["summary"] = {
        "version": _cli.VERSION, "python": platform.python_version(), "os": platform.system(),
        "traps_clean": f"{tp}/{len(results['traps'])}", "defects_caught": f"{dp}/{len(results['defects'])}",
        "seconds": round(time.perf_counter() - started, 3), "pass": tp == len(results["traps"]) and dp == len(results["defects"]),
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    # build both outputs first, then write (a failure while formatting leaves the old files intact)
    js = json.dumps(results, ensure_ascii=False, indent=2) + "\n"
    md = to_markdown(results)
    (out_dir / "results.json").write_text(js, encoding="utf-8")
    (out_dir / "RESULTS.md").write_text(md, encoding="utf-8")
    return results


def to_markdown(r: dict) -> str:
    s = r["summary"]
    rows = ["# Validator benchmark", "",
            f"moadian-invoice {s['version']} · Python {s['python']} · {s['os']} · {s['seconds']} s", "",
            f"**{'PASS' if s['pass'] else 'FAIL'}** — valid traps clean: {s['traps_clean']} · seeded defects caught at "
            f"the root: {s['defects_caught']}", "", "## Traps (valid invoices that must stay clean)", "",
            "| trap | result |", "|---|---|"]
    for t in r["traps"]:
        rows.append(f"| {t['name']} | {'clean' if t['pass'] else 'FLAGGED: ' + '; '.join(t['errors'] + t['warnings'])[:200]} |")
    rows += ["", "## Seeded defects", "", "| defect | expected | result | likely code |", "|---|---|---|---|"]
    for d in r["defects"]:
        res = "caught" if d["pass"] else ("missed" if not d["found"] else "extra errors: " + ", ".join(d["unexpected_root_errors"]))
        rows.append(f"| {d['name']} | {d['expected']} | {res} | {d['code_hint'] or ''} |")
    return "\n".join(rows) + "\n"


def main(argv=None) -> int:
    _cli.setup_stdout()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    _cli.add_version(ap, "bench")
    ap.add_argument("--out", default=str(Path(__file__).resolve().parent))
    args = ap.parse_args(argv)
    r = run(Path(args.out))
    print(json.dumps(r["summary"], ensure_ascii=False))
    for kind in ("traps", "defects"):
        for item in r[kind]:
            if not item["pass"]:
                print(f"FAIL {kind[:-1]}: {item['name']}: {json.dumps(item, ensure_ascii=False)[:400]}")
    return 0 if r["summary"]["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
