import json
from pathlib import Path

import pytest

import _ids
import validate_invoice as V

EX = Path(__file__).resolve().parent.parent / "skills" / "moadian-invoice" / "examples"

# Test vectors from persian-tools (PyPI 0.0.11 tests/test_legal_id.py, test_national_id.py;
# npm 4.0.4 README). The first two legal ids are marked there as "valid and registered".
LEGAL_VALID = ["10380284790", "10100387143", "77111986110", "18061055669", "15292247120", "42118547230",
               "27388385445", "55828465992", "32882926778", "97006806007", "21272129339", "18706641333"]
LEGAL_INVALID = ["84735069516", "65399567978", "99969101031", "15826563190", "11053639140", "18090089802",
                 "11111111111", "10380284792", "10380285692", "123001000", "097482083013", "0974820830a"]
NATIONAL_VALID = ["0068415941", "0499370899", "0790419904", "0084575948", "0963695398", "0684159414",
                  "0067749828", "0650451252", "1583250689", "4032152314", "0076229645"]
NATIONAL_INVALID = ["0000000000", "4271427685", "0200203041", "0684159415", "068415941d", "06841594156",
                    "0123000000", "1111111111"]


@pytest.mark.parametrize("code", LEGAL_VALID)


def test_legal_valid(code):
    assert _ids.legal_id_ok(code)


@pytest.mark.parametrize("code", LEGAL_INVALID)


def test_legal_invalid(code):
    assert not _ids.legal_id_ok(code)


@pytest.mark.parametrize("code", NATIONAL_VALID)


def test_national_valid(code):
    assert _ids.national_code_ok(code)


@pytest.mark.parametrize("code", NATIONAL_INVALID)


def test_national_invalid(code):
    assert not _ids.national_code_ok(code)


def test_check_auto_and_uncheckable():
    assert _ids.check("0499370899", "auto") is None
    assert "national" in _ids.check("4271427685", "auto")
    assert "legal" in _ids.check("10380285692", "auto")
    assert _ids.check("123456789012", "auto") is None      # foreign-national code: no sourced algorithm
    assert _ids.check("12345678901234", "legal") is None   # 14-digit economic code: not checked
    assert _ids.check(10380285692, "legal") is None        # non-strings are the type checker's job


def test_persian_digits_not_accepted():
    fa = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")
    assert not _ids.national_code_ok("0499370899".translate(fa))
    assert not _ids.legal_id_ok("10380284790".translate(fa))
    assert _ids.check("0499370899".translate(fa), "auto") is None  # format error: field checks report it


def load(name):
    return json.loads((EX / name).read_text(encoding="utf-8"))


def warns(res):
    return {w["path"]: w for w in res["warnings"] if w["rule"] == "id-check-digit"}


def test_examples_use_valid_ids():
    for name in ("invoice-type1-minimal.json", "invoice-type1-full.json"):
        assert not warns(V.validate(load(name)))


def test_bad_seller_and_buyer_ids_warn_but_stay_valid():
    inv = load("invoice-type1-minimal.json")
    inv["header"].update(tins="10101234567", tinb="10380285692")
    res = V.validate(inv)
    w = warns(res)
    assert res["ok"]  # warnings only: the algorithm is not from an official INTA document
    assert w["header.tins"]["code_hint"] == "0300901"
    assert w["header.tinb"]["code_hint"] == "0301201"


def test_natural_person_bid_checked_as_national_code():
    inv = load("invoice-type1-minimal.json")
    h = inv["header"]
    del h["tinb"]
    h.update(tob=1, bid="0012345678", bpc="1234567890")
    assert "header.bid" in warns(V.validate(inv))
    h["bid"] = "0012345679"
    assert not warns(V.validate(inv))


def test_civil_partnership_tinb_not_checked():
    inv = load("invoice-type1-minimal.json")
    inv["header"].update(tob=3, tinb="10380285692")
    assert "header.tinb" not in warns(V.validate(inv))


def test_payment_pid_checked():
    inv = load("invoice-type1-minimal.json")
    inv["payments"] = [{"pmt": 4, "pid": "4271427685"}]
    assert "payments[0].pid" in warns(V.validate(inv))
