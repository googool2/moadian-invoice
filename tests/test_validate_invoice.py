import copy
import json
from pathlib import Path

import pytest

import taxid as T
import validate_invoice as V

EX = Path(__file__).resolve().parent.parent / "examples"


def load(name):
    return json.loads((EX / name).read_text(encoding="utf-8"))


@pytest.fixture
def good():
    return load("invoice-type1-minimal.json")


def paths(res, kind="errors"):
    return [e["path"] for e in res[kind]]


@pytest.mark.parametrize("name", ["invoice-type1-minimal.json", "invoice-type1-full.json"])
def test_valid_examples_pass(name):
    res = V.validate(load(name))
    assert res["ok"], res["errors"]
    assert res["warning_count"] == 0, res["warnings"]


def test_official_connection_spec_example_passes():
    # RC_TICS.IS v1.6 worked example (amounts verbatim), with a valid taxid
    ind = 18463 * 86_400_000
    inv = {"header": {"taxid": "DEF5GH0481F000000000C2", "indatim": ind, "inty": 1, "inno": "000000000C",
                      "inp": 1, "ins": 1, "tins": "14003778990", "tob": 2, "tinb": "10101234567",
                      "tprdis": 20000, "tdis": 500, "tadis": 19500, "tvam": 1755, "todam": 0, "tbill": 21255,
                      "setm": 2},
           "body": [{"sstid": "2330004219206", "am": 2, "fee": 10000, "prdis": 20000, "dis": 500,
                     "adis": 19500, "vra": 9, "vam": 1755, "tsstam": 21255}], "payments": []}
    assert V.validate(inv)["ok"]


def test_invalid_arith_example_reports_exact_errors():
    res = V.validate(load("invoice-invalid-arith.json"))
    assert not res["ok"]
    got = {(e["path"], e.get("expected")) for e in res["errors"]}
    assert ("body[0].prdis", 1000000) in got
    assert ("header.tvam", 190000) in got
    assert ("header.tbill", 2090001) in got
    assert "header.cap" in paths(res)
    assert res["error_count"] == 4
    assert "header.insp" in paths(res, "warnings")


def test_discount_is_line_total_not_per_unit(good):
    b = good["body"][0]
    b.update(am=2, fee=25000000, dis=1000000, adis=49000000, vam=4900000, tsstam=53900000)
    good["header"].update(tdis=1000000, tadis=49000000, tvam=4900000, tbill=53900000)
    assert V.validate(good)["ok"]
    # moadian-full style: dis multiplied by am
    b.update(adis=48000000)
    res = V.validate(good)
    assert "body[0].adis" in paths(res)


def test_vam_truncated_not_rounded(good):
    b = good["body"][0]
    b.update(fee=99999, prdis=99999, adis=99999, vam=10000, tsstam=109999)  # 9999.9 rounds to 10000
    good["header"].update(tprdis=99999, tadis=99999, tvam=10000, tbill=109999)
    res = V.validate(good)
    assert any(e["path"] == "body[0].vam" and e["expected"] == 9999 for e in res["errors"])
    assert res["errors"][0]["code_hint"] == "0204501"


def test_dis_greater_than_prdis(good):
    good["body"][0]["dis"] = 60000000
    assert "body[0].dis" in paths(V.validate(good))


def test_missing_required_field(good):
    del good["header"]["tvam"]
    res = V.validate(good)
    assert any(e["path"] == "header.tvam" and e["rule"] == "required" for e in res["errors"])


def test_type1_legal_buyer_needs_tinb(good):
    del good["header"]["tinb"]
    assert "header.tinb" in paths(V.validate(good))


def test_type1_natural_buyer_with_bid_and_postal_code_ok(good):
    h = good["header"]
    del h["tinb"]
    h.update(tob=1, bid="0012345678", bpc="1234567890")
    assert V.validate(good)["ok"]
    del h["bpc"]
    assert "header.tinb" in paths(V.validate(good))


def test_type2_does_not_need_buyer_or_setm(good):
    h = good["header"]
    for k in ("tob", "tinb", "setm"):
        del h[k]
    h["inty"] = 2
    res = V.validate(good)
    assert res["ok"], res["errors"]


def test_type2_rejects_contracting_pattern(good):
    good["header"].update(inty=2, inp=4)
    assert "header.inp" in paths(V.validate(good))


def test_bad_enums(good):
    good["header"].update(inty=4, ins=7, tob=9)
    res = V.validate(good)
    assert {"header.inty", "header.ins", "header.tob"} <= set(paths(res))


def test_return_not_allowed_for_export(good):
    good["header"].update(inp=7, ins=4, irtaxid=good["header"]["taxid"])
    assert "header.ins" in paths(V.validate(good))


def test_reference_invoice_needs_irtaxid(good):
    good["header"]["ins"] = 2
    assert "header.irtaxid" in paths(V.validate(good))


def test_cancellation_header_only_ok(good):
    h = good["header"]
    ref = h["taxid"]
    new = T.generate("A11216", h["indatim"], 99)
    inv = {"header": {"taxid": new, "indatim": h["indatim"], "inno": new[11:21], "ins": 3, "irtaxid": ref,
                      "tins": h["tins"]}, "body": [], "payments": []}
    res = V.validate(inv)
    assert res["ok"], res["errors"]


def test_setm3_requires_cap_insp_summing_to_net(good):
    h = good["header"]
    h.update(setm=3, cap=30000000, insp=10000000)  # net is 50,000,000
    res = V.validate(good)
    assert any(e["path"] == "header.cap" and e["expected"] == 50000000 for e in res["errors"])
    h.update(insp=20000000)
    assert V.validate(good)["ok"]
    del h["insp"]
    assert "header.insp" in paths(V.validate(good))


def test_zero_vat_patterns(good):
    good["header"]["inp"] = 14
    assert "body[0].vra" in paths(V.validate(good))


def test_wrong_types(good):
    good["header"]["tins"] = 10101234567           # number instead of digit string
    good["body"][0]["sstid"] = "23300042192"       # 11 digits
    good["body"][0]["vam"] = 5000000.5             # rial amounts are integers
    good["header"]["inty"] = "1"
    res = V.validate(good)
    p = paths(res)
    assert {"header.tins", "body[0].sstid", "body[0].vam", "header.inty"} <= set(p)


def test_field_in_wrong_section(good):
    good["header"]["vam"] = 1
    assert "header.vam" in paths(V.validate(good))


def test_unknown_field_warns(good):
    good["header"]["foo"] = 1
    res = V.validate(good)
    assert res["ok"] and "header.foo" in paths(res, "warnings")


def test_bad_taxid_check_digit(good):
    t = good["header"]["taxid"]
    good["header"]["taxid"] = t[:-1] + str((int(t[-1]) + 1) % 10)
    res = V.validate(good)
    assert any(e["code_hint"] == "0300101" for e in res["errors"])


def test_taxid_date_must_match_indatim(good):
    good["header"]["indatim"] += 86_400_000
    assert any(e["path"] == "header.taxid" for e in V.validate(good)["errors"])


def test_inno_format_and_mismatch(good):
    good["header"]["inno"] = "12"
    res = V.validate(good)
    assert any(e["code_hint"] == "0100504" for e in res["errors"])
    good["header"]["inno"] = "000000FFFF"
    res = V.validate(good)
    assert res["ok"] and any(w.get("code_hint") == "1300501" for w in res["warnings"])


def test_out_of_pattern_warning(good):
    good["header"]["billid"] = "123"
    res = V.validate(good)
    assert res["ok"] and any(w["path"] == "header.billid" for w in res["warnings"])


def test_date_window(good):
    ind = good["header"]["indatim"]
    assert not V.validate(good, now_ms=ind - 60_000)["ok"]
    assert V.validate(good, now_ms=ind + 3_600_000)["ok"]
    assert V.validate(good, now_ms=ind + 8 * 86_400_000)["warnings"]


def test_tax17_bound(good):
    good["header"]["tax17"] = 6000000
    assert "header.tax17" in paths(V.validate(good))


def test_type3_needs_payment_data(good):
    good["header"]["inty"] = 3
    res = V.validate(good)
    assert "payments" in paths(res)
    assert any("inty=3" in n for n in res["notes"])


def test_structure_errors():
    assert not V.validate([])["ok"]
    assert not V.validate({"body": []})["ok"]
    assert not V.validate({"header": {}, "body": {}})["ok"]


def test_gold_pattern_arithmetic(good):
    b = good["body"][0]
    b.update(fee=100000000, prdis=100000000, dis=0, consfee=5000000, spro=3000000, bros=2000000, tcpbs=10000000,
             adis=110000000, vra=10, vam=11000000, tsstam=121000000)
    good["header"].update(inp=3, tprdis=100000000, tadis=110000000, tvam=11000000, tbill=121000000)
    res = V.validate(good)
    assert res["ok"], res["errors"]
    b["tcpbs"] = 9000000
    assert "body[0].tcpbs" in paths(V.validate(good))


def test_cli(tmp_path, capsys):
    assert V.main([str(EX / "invoice-type1-minimal.json")]) == 0
    assert json.loads(capsys.readouterr().out)["ok"]
    assert V.main([str(EX / "invoice-invalid-arith.json"), "--text"]) == 1
    assert "INVALID" in capsys.readouterr().out
    bad = tmp_path / "bad.json"
    bad.write_text("{not json", encoding="utf-8")
    assert V.main([str(bad)]) == 1


def test_validate_is_pure(good):
    before = copy.deepcopy(good)
    V.validate(good)
    assert good == before
