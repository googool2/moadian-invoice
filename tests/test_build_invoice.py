import json
import sys
from datetime import date
from pathlib import Path

import pytest

import _moadian
import build_invoice as B
import validate_invoice as V

try:
    LIB = _moadian.load()
except _moadian.MoadianFullMissing:  # pragma: no cover
    LIB = None
needs_lib = pytest.mark.skipif(LIB is None, reason="moadian-full not installed")
EX = Path(__file__).resolve().parent.parent / "skills" / "moadian-invoice" / "examples"


@pytest.fixture
def spec():
    return {
        "memory_id": "A11216", "seller_tin": "10101234565", "date": "1405-02-01", "serial": 26,
        "type": 1, "pattern": 1, "subject": 1, "settlement": 1,
        "buyer": {"type": 2, "tin": "14011576540"},
        "items": [{"sstid": "2330004219206", "description": "پرینتر", "quantity": 2,
                   "unit_price": 120000000, "discount": 4000000, "vat_rate": 10, "unit": "1627"}],
    }


@pytest.mark.parametrize("jalali,greg", [
    ((1399, 4, 30), date(2020, 7, 20)),   # RC_DCPS.SN_V1.3 worked example
    ((1403, 1, 1), date(2024, 3, 20)),
    ((1403, 12, 30), date(2025, 3, 20)),  # leap year
    ((1404, 1, 1), date(2025, 3, 21)),
    ((1405, 2, 1), date(2026, 4, 21)),
])
def test_jalali(jalali, greg):
    assert B.jalali_to_gregorian(*jalali) == greg


def test_parse_when_date_only_is_noon_tehran():
    assert int(B.parse_when({"date": "1405-02-01"}).timestamp() * 1000) == 1776760200000
    assert int(B.parse_when({"date": "۱۴۰۵/۰۲/۰۱"}).timestamp() * 1000) == 1776760200000
    assert int(B.parse_when({"indatim": 1776760200000}).timestamp() * 1000) == 1776760200000


@needs_lib
def test_loader_imports_no_network_code():
    import subprocess

    code = ("import sys; sys.path.insert(0, 'scripts'); import _moadian; _moadian.load(); "
            "print(sorted(m for m in ('requests', 'authlib', 'cryptography') if m in sys.modules))")
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True,
                         cwd=Path(__file__).resolve().parent.parent / "skills" / "moadian-invoice", check=True).stdout.strip()
    assert out == "[]"


@needs_lib
def test_build_basic(spec, tmp_path):
    res = B.build(spec, state_dir=str(tmp_path))
    inv = res["invoice"]
    b, h = inv["body"][0], inv["header"]
    assert (b["prdis"], b["dis"], b["adis"], b["vam"], b["tsstam"]) == (240000000, 4000000, 236000000, 23600000, 259600000)
    assert (h["tprdis"], h["tdis"], h["tadis"], h["tvam"], h["tbill"]) == (240000000, 4000000, 236000000, 23600000, 259600000)
    assert h["cap"] is None and h["insp"] is None and h["indati2m"] is None
    assert h["taxid"] == "A1121605054000000001A5" and h["inno"] == "000000001A"
    assert V.validate(inv)["ok"]


@needs_lib
def test_build_reports_library_defects(spec, tmp_path):
    res = B.build(spec, state_dir=str(tmp_path))
    fixed = {c["path"]: c for c in res["corrections"]}
    assert fixed["body[0].dis"]["moadian_full"] == 8000000  # library multiplied dis by am
    assert fixed["header.taxid"]["moadian_full"] != fixed["header.taxid"]["corrected"]
    assert fixed["header.insp"]["moadian_full"] is not None  # library declared credit on a cash invoice


@needs_lib
def test_raw_library_output_fails_validation(tmp_path):
    from datetime import datetime, timezone

    # Pin serial/date to the RC_DCPS.SN_V1.3 example: moadian-full 0.0.2 gives ...C7, the official digit is ...C2.
    # (With a random serial the wrong digit matches the right one ~10% of the time.)
    builder = LIB.InvoiceBuilder("DEF5GH", "10101234565", storage_path=str(tmp_path))
    builder.serial_manager = B._FixedSerial(12)
    builder.set_invoice_time(datetime(2020, 7, 20, 8, 0, tzinfo=timezone.utc))
    builder.set_buyer("14011576540", 2)
    builder.add_item(LIB.InvoiceItem("2330004219206", "x", 120000000, am=2, dis=4000000, vra=10))
    raw = builder.build_dict()
    res = V.validate(raw)
    assert not res["ok"]
    assert raw["header"]["taxid"] == "DEF5GH0481F000000000C7"
    assert any(e["path"] == "header.taxid" and "expected 2" in e["message"] for e in res["errors"])
    assert any(e["path"] == "header.cap" for e in res["errors"])


@needs_lib
def test_build_mixed_settlement(spec, tmp_path):
    spec.update(settlement=3, cash_amount=200000000)
    h = B.build(spec, state_dir=str(tmp_path))["invoice"]["header"]
    assert h["cap"] + h["insp"] == h["tadis"]
    assert V.validate(B.build(spec, state_dir=str(tmp_path))["invoice"])["ok"]


@needs_lib
def test_build_type2_without_buyer(spec, tmp_path):
    spec.update(type=2)
    del spec["buyer"]
    inv = B.build(spec, state_dir=str(tmp_path))["invoice"]
    assert inv["header"]["tob"] is None and inv["header"]["tinb"] is None and inv["header"]["setm"] is None
    assert V.validate(inv)["ok"], V.validate(inv)["errors"]


@needs_lib
def test_build_cancellation(spec, tmp_path):
    ref = B.build(spec, state_dir=str(tmp_path))["taxid"]
    spec.update(subject=3, reference_taxid=ref, serial=27, items=[])
    inv = B.build(spec, state_dir=str(tmp_path))["invoice"]
    assert inv["body"] == [] and inv["header"]["irtaxid"] == ref and inv["header"]["ins"] == 3
    assert V.validate(inv)["ok"], V.validate(inv)["errors"]


@needs_lib
def test_build_uses_serial_manager_when_no_serial(spec, tmp_path):
    del spec["serial"]
    res = B.build(spec, state_dir=str(tmp_path))
    assert len(res["inno"]) == 10
    assert (tmp_path / "serial_history_A11216.json").exists()
    assert V.validate(res["invoice"])["ok"]


@needs_lib
def test_cli_yaml_to_file(tmp_path, capsys):
    out = tmp_path / "inv.json"
    rc = B.main([str(EX / "build-input.yaml"), "-o", str(out), "--state-dir", str(tmp_path)])
    report = json.loads(capsys.readouterr().out)
    assert rc == 0 and report["ok"] and out.exists()
    assert json.loads(out.read_text(encoding="utf-8"))["header"]["tbill"] == 259600000


@needs_lib
def test_cli_full_example_matches_committed(tmp_path, capsys):
    out = tmp_path / "full.json"
    assert B.main([str(EX / "build-input-full.yaml"), "-o", str(out), "--state-dir", str(tmp_path)]) == 0
    assert json.loads(out.read_text(encoding="utf-8")) == json.loads((EX / "invoice-type1-full.json").read_text(encoding="utf-8"))


def test_cli_bad_input(tmp_path, capsys):
    bad = tmp_path / "bad.yaml"
    bad.write_text("seller_tin: 1\n", encoding="utf-8")
    assert B.main([str(bad), "--state-dir", str(tmp_path)]) == 2
    assert not json.loads(capsys.readouterr().out)["ok"]


@needs_lib
def test_no_unit_means_no_mu(spec, tmp_path):
    del spec["items"][0]["unit"]
    res = B.build(spec, state_dir=str(tmp_path))
    assert res["invoice"]["body"][0]["mu"] is None  # not moadian-full's default "164"
    assert any(c["path"] == "body[0].mu" and c["moadian_full"] == "164" for c in res["corrections"])


@needs_lib
def test_no_description_means_no_sstt(spec, tmp_path):
    del spec["items"][0]["description"]
    res = B.build(spec, state_dir=str(tmp_path))
    assert res["invoice"]["body"][0]["sstt"] is None
    assert V.validate(res["invoice"])["ok"]
