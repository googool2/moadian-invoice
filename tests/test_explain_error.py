import json

import explain_error as E

ROWS = E.load_table()
FIELDS = E.load_field_numbers()


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
    assert st["field"] == "dis" and st["severity"].startswith("error") and st["detail_meaning"] == "exclusive min/max"


def test_warning_severity():
    st = E.decode_structure("1300501", FIELDS)
    assert st["severity"].startswith("warning") and st["field"] == "inno"


def test_transport_code_not_structurally_decoded():
    assert E.decode_structure("04111", FIELDS) is None
    assert E.explain(["04111"], ROWS, FIELDS)["results"][0]["found"]


def test_unverified_flag():
    row = next(r for r in ROWS if r["code"] == "0300902")
    assert row["unverified"]


def test_field_numbers_loaded():
    assert FIELDS["001"] == "taxid" and FIELDS["045"] == "vam" and FIELDS["107"] == "insr"


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
