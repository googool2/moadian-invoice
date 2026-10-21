import json

import explain_error as E

ROWS = E.load_table()
FIELDS = E.load_field_numbers()
ALIASES = E.load_aliases()


def test_table_parses_many_rows():
    assert len(ROWS) >= 60
    assert all(r["code"] and r["meaning_en"] and r["source"] for r in ROWS)


def test_known_code():
    res = E.explain(["0300101"], ROWS, FIELDS)["results"][0]
    assert res["found"]
    assert res["matches"][0]["fields"] == "taxid"
    assert res["structure"]["field"] == "taxid"


def test_persian_digits_normalized():
    res = E.explain(["۰۳۰۰۱۰۱"], ROWS, FIELDS)["results"][0]
    assert res["found"] and res["matches"][0]["code"] == "0300101"


def test_unknown_code_is_not_invented_but_decoded():
    res = E.explain(["0104205"], ROWS, FIELDS)["results"][0]
    assert not res["found"] and res["matches"] == []
    assert res["note"] and "Do not guess" in res["note"]
    st = res["structure"]
    assert st["field"] == "dis" and st["severity"].startswith("error") and st["detail_meaning"] == "exclusive max/min"


def test_warning_severity():
    st = E.decode_structure("1300501", FIELDS)
    assert st["severity"].startswith("warning") and st["field"] == "inno"


def test_transport_code_not_structurally_decoded():
    assert E.decode_structure("04111", FIELDS) is None
    assert E.explain(["04111"], ROWS, FIELDS)["results"][0]["found"]


def test_unverified_flag(tmp_path):
    md = tmp_path / "errors.md"
    md.write_text("| code | message_fa | meaning_en | fields | fix | source |\n|---|---|---|---|---|---|\n"
                  "| 0399901 | x | y [UNVERIFIED] | f | z | E1 |\n| 0399902 | x | y | f | z | O1 |\n", encoding="utf-8")
    rows = {r["code"]: r for r in E.load_table(md)}
    assert rows["0399901"]["unverified"] and not rows["0399902"]["unverified"]


def test_codes_confirmed_by_official_lists():
    """Codes printed in RC_TXPS.EC_V02 Table 9 / RE_V01 headings must cite O1/O2."""
    by_code = {r["code"]: r for r in ROWS}
    official = {"0300101": "O1", "02002": "O1", "0304401": "O1", "0300601": "O1", "0301201": "O1",
                "0300902": "O1", "0300903": "O1", "1300501": "O1", "04111": "O1", "4101": "O1", "4018": "O1",
                "0204501": "O2", "0303301": "O2", "00012": "O2", "0101304": "O2", "0101204": "O2", "0101104": "O2"}
    for code, src in official.items():
        assert src in by_code[code]["source"].split(), code
        assert not by_code[code]["unverified"], code


def test_short_forms_map_to_full_codes():
    assert ALIASES["0301"] == "0300101" and ALIASES["0012"] == "00012" and ALIASES["011204"] == "0101204"
    res = E.explain(["0344"], ROWS, FIELDS, ALIASES)["results"][0]
    assert res["short_form_of"] == "0304401" and res["found"]
    assert res["matches"][0]["code"] == "0304401"
    for short, full in ALIASES.items():
        assert any(r["code"] == full for r in ROWS), (short, full)


def test_export_vat_advice_matches_validator():
    """O1 and V7.8 say export lines carry vra 0; the older RE_V01 said non-zero. Keep errors.md
    consistent with the validator's rule (_spec.ZERO_VAT_PATTERNS)."""
    import _spec
    row = next(r for r in ROWS if r["code"] == "0304401")
    assert 7 in _spec.ZERO_VAT_PATTERNS
    assert "vra must be 0" in row["fix"] and "non-zero rate" not in row["fix"]


def test_old_api_and_new_transport_codes():
    by_code = {r["code"]: r for r in ROWS}
    for code in ("4001", "4212", "5202", "5207", "04133", "05159"):
        assert code in by_code and "O1" in by_code[code]["source"], code


def test_field_numbers_loaded():
    assert FIELDS["001"] == "taxid" and FIELDS["045"] == "vam" and FIELDS["107"] == "insr"
    assert FIELDS["077"] == "pspd" and FIELDS["080"] == "hs"  # last rows of O1 Table 8


def test_codes_from_response():
    resp = {"result": [{"data": {"error": [{"code": "0300101", "message": "x"}],
                                 "warning": [{"code": "1300501"}]}}]}
    assert E.codes_from_response(resp) == ["0300101", "1300501"]


def test_text_search():
    res = E.explain(["regex"], ROWS, FIELDS)["results"][0]
    assert res["found"] and len(res["matches"]) > 1


def test_cli_from_response(tmp_path, capsys):
    f = tmp_path / "resp.json"
    f.write_text(json.dumps({"data": {"error": [{"code": "0204501"}]}}), encoding="utf-8")
    assert E.main(["--from-response", str(f)]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["results"][0]["matches"][0]["fields"] == "vam"


def test_cli_unknown_exit_code(capsys):
    assert E.main(["9999999"]) == 1
