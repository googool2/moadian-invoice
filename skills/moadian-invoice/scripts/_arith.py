"""Arithmetic checks (references/arithmetic-rules.md) used by validate_invoice.py."""

from __future__ import annotations

from decimal import Decimal

from _common import HUNDRED, Report, _plain, code_hint, num, trunc


class Line:
    """One body line. Each check compares the given value with the value expected from the
    already-corrected upstream fields, then keeps the corrected value, so a single wrong
    number is reported once at its root and every field derived from it says so."""

    def __init__(self, rep: Report, idx: int, raw: dict) -> None:
        self.rep, self.p = rep, f"body[{idx}]"
        self.v = {k: num(raw.get(k)) for k in (
            "am", "fee", "cfee", "exr", "prdis", "dis", "adis", "vra", "vam", "odr", "odam", "olr", "olam",
            "tsstam", "ssrv", "consfee", "spro", "bros", "tcpbs", "sovat", "vba", "nw", "sscv", "vop", "cop")}
        self.wrong: list[str] = []

    def check(self, field, expected, rule, source, code=None, inputs=(), accept=()):
        actual = self.v[field]
        if expected is None or actual is None:
            return
        if actual != expected and actual not in accept:
            roots = [f for f in inputs if f in self.wrong]
            why = f" (follows from the corrected {', '.join(roots)})" if roots else ""
            self.rep.error(f"{self.p}.{field}", f"{field} should be {_plain(expected)}, found {_plain(actual)}{why}",
                           rule, source, expected=expected, actual=actual, code=None if roots else code)
            self.wrong.append(field)
            self.v[field] = expected


def check_line(rep: Report, i: int, b: dict, inp) -> dict:
    ln = Line(rep, i, b)
    g = ln.v
    if inp == 7:  # export: base is the rial value per customs licence (S1 §7-42, §7-51)
        if g["ssrv"] is not None and g["vra"] is not None:
            ln.check("vam", trunc(g["ssrv"] * g["vra"] / HUNDRED), "R7 export", "S1 §7-42", "0204501")
        base_key = "ssrv"
    else:
        if inp == 2 and g["cfee"] is not None and g["exr"] is not None:
            exp = trunc(g["cfee"] * g["exr"])
        elif inp == 6 and g["fee"] is not None:
            exp = trunc(g["fee"])
        elif g["am"] is not None and g["fee"] is not None:
            exp = trunc(g["am"] * g["fee"])
        else:
            exp = None
        ln.check("prdis", exp, "R4 prdis = am × fee (truncated)", "S1 §7-38", "0204101")
        if g["dis"] is not None and g["prdis"] is not None and g["dis"] > g["prdis"]:
            rep.error(ln.p + ".dis", "dis (the line's total discount) cannot exceed prdis", "R5", "S1 §7-39",
                      expected=f"<= {_plain(g['prdis'])}", actual=g["dis"], code="0204201")
        if inp == 3:
            if None not in (g["consfee"], g["spro"], g["bros"]):
                ln.check("tcpbs", g["consfee"] + g["spro"] + g["bros"], "R19", "S1 §7-47")
            exp = None if None in (g["prdis"], g["dis"], g["tcpbs"]) else g["prdis"] + g["tcpbs"] - g["dis"]
        else:
            exp = None if None in (g["prdis"], g["dis"]) else g["prdis"] - g["dis"]
        ln.check("adis", exp, "R6 adis = prdis − dis", "S1 §7-40", "0204301", inputs=("prdis", "tcpbs"))
        base_key = "adis"
        if g["vra"] is not None:
            if inp == 3 and g["tcpbs"] is not None and g["prdis"] is not None:
                a, c = g["tcpbs"] * 10 / HUNDRED, g["prdis"] * g["vra"] / HUNDRED
                ln.check("vam", trunc(a + c), "R7 gold", "S1 §7-42", "0204501", ("prdis", "tcpbs"),
                         accept=(trunc(a) + trunc(c),))
            elif inp == 2 and g["sovat"] is not None:
                ln.check("vam", trunc(g["sovat"] * g["vra"] / HUNDRED), "R7 currency", "S1 §7-42", "0204501")
            elif inp == 9 and g["vba"] is not None and g["am"] is not None:
                ln.check("vam", trunc(g["am"] * g["vba"]), "R7 petroleum", "S1 §7-42", "0204501")
            elif g["adis"] is not None:
                ln.check("vam", trunc(g["adis"] * g["vra"] / HUNDRED), "R7 vam = adis × vra / 100 (truncated)",
                         "S1 §7-42", "0204501", ("prdis", "adis"))
    base = g[base_key]
    rate_base = g["tcpbs"] if inp == 3 else base
    for amt, rate in (("odam", "odr"), ("olam", "olr")):
        if g[rate] is not None and rate_base is not None:
            ln.check(amt, trunc(rate_base * g[rate] / HUNDRED), "R8", "S1 §7-43", inputs=("prdis", "adis"))
        if g["vra"] == 0 and (g[amt] or 0) != 0:
            rep.error(f"{ln.p}.{amt}", f"{amt} must be 0 when vra is 0", "R8", "S1 §7-43", actual=g[amt])
    if base is not None and g["vam"] is not None:
        ln.check("tsstam", base + g["vam"] + (g["odam"] or 0) + (g["olam"] or 0),
                 "R9 tsstam = adis + vam + odam + olam", "S1 §7-51", inputs=("prdis", "adis", "vam", "odam", "olam"))
    return {"values": g, "wrong": ln.wrong}


def _eq(rep, path, field, expected, actual, rule, source, code=None, note=""):
    if expected is None or actual is None:
        return
    if expected != actual:
        rep.error(path, f"{field} should be {_plain(expected)}, found {_plain(actual)}{note}", rule, source,
                  expected=expected, actual=actual, code=None if note else code)


def check_arithmetic(rep: Report, inv, inty, inp, ins) -> dict:
    h = inv["header"]
    body = [b for b in inv.get("body") or [] if isinstance(b, dict)]
    sums = {k: Decimal(0) for k in ("prdis", "dis", "adis", "vam", "odam", "olam", "tsstam", "nw", "ssrv", "sscv", "vop")}
    seen, line_wrong = set(), set()
    for i, b in enumerate(body):
        res = check_line(rep, i, b, inp)
        line_wrong.update(res["wrong"])
        for k in sums:
            if res["values"].get(k) is not None:
                sums[k] += res["values"][k]
                seen.add(k)
    if ins == 3 and not body:
        return {}
    totals = [("tprdis", "prdis", "S1 §7-13"), ("tdis", "dis", "S1 §7-14"), ("tadis", "adis", "S1 §7-15"),
              ("tvam", "vam", "S1 §7-16"), ("tbill", "tsstam", "S1 §7-18"), ("tonw", "nw", "S1 §7-19"),
              ("torv", "ssrv", "S1 §7-20"), ("tocv", "sscv", "S1 §7-21"), ("tvop", "vop", "S1 §7-25")]
    for hf, bf, src in totals:
        if bf in seen:
            note = f" (Σ of the corrected body {bf})" if bf in line_wrong else ""
            _eq(rep, f"header.{hf}", hf, sums[bf], num(h.get(hf)), f"R10 {hf} = Σ {bf}", src, code_hint(hf, "2", "01"), note)
    if "odam" in seen or "olam" in seen or h.get("todam") is not None:
        _eq(rep, "header.todam", "todam", sums["odam"] + sums["olam"], num(h.get("todam")), "R10 todam = Σodam + Σolam",
            "S1 §7-17", code_hint("todam", "2", "01"))
    # use the corrected body sums when there are lines, so one root error is not reported twice
    tbill = sums["tsstam"] if "tsstam" in seen else num(h.get("tbill"))
    tvam = sums["vam"] if "vam" in seen else (num(h.get("tvam")) or 0)
    todam = sums["odam"] + sums["olam"] if {"odam", "olam"} & seen else (num(h.get("todam")) or 0)
    if (num(h.get("tprdis")) or 0) <= 0 and spec.status("tprdis", inty or 0, inp or 0) == "M":
        rep.error("header.tprdis", "tprdis must be greater than 0", "R10", "S1 §7-13", code="0102205")
    cap, insp = num(h.get("cap")), num(h.get("insp"))
    if tbill is not None:
        net = tbill - tvam - todam
        if h.get("setm") == 3 and cap is not None and insp is not None:
            _eq(rep, "header.cap", "cap + insp", net, cap + insp, "R12/R13 cap + insp = tbill − tvam − todam",
                "S1 §7-23, §7-24")
            for f, v in (("cap", cap), ("insp", insp)):
                if v <= 0:
                    rep.error(f"header.{f}", f"{f} must be > 0 when setm=3", "R12/R13", "S1 §7-23, §7-24", actual=v)
        elif cap is not None and cap > net:
            rep.error("header.cap", "cap is the cash amount EXCLUDING VAT and other taxes, so it cannot exceed "
                      "tbill − tvam − todam (moadian-full 0.0.2 sets cap=tbill)", "R12", "S1 §7-23",
                      expected=f"<= {_plain(net)}", actual=cap)
    if num(h.get("tax17")) is not None and num(h.get("tax17")) > tvam:
        rep.error("header.tax17", "tax17 cannot exceed tvam", "R17", "S1 §7-26", actual=h.get("tax17"))
    for i, pmt in enumerate(inv.get("payments") or []):
        pv = num(pmt.get("pv")) if isinstance(pmt, dict) else None
        if pv is None:
            continue
        if h.get("setm") == 2 and pv != 0:
            rep.error(f"payments[{i}].pv", "pv must be 0 on a credit (setm=2) invoice", "R20", "S1 §7-60", actual=pv)
        if tbill is not None and pv > tbill:
            rep.error(f"payments[{i}].pv", "pv cannot exceed tbill", "R20", "S1 §7-60", actual=pv)
    return {k: _plain(v) for k, v in sums.items() if k in seen}
