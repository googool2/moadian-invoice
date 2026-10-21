import json

import pytest

import taxid as T

DAY = 86_400_000

# RC_DCPS.SN_V1.3 Appendix 1 (official) — memory id DEF5GH, day 18463
OFFICIAL = [
    (12, "DEF5GH0481F000000000C2"),
    (8173, "DEF5GH0481F0000001FED8"),
    (2572613409, "DEF5GH0481F009956F7211"),
]
# Real taxids accepted by the system (secondary source, see references/workflow.md)
REAL_ACCEPTED = ["A41XRD050B1006A5E4C549", "A2HP31050B0006A607FE94"]


@pytest.mark.parametrize("serial,expected", OFFICIAL)


def test_official_examples(serial, expected):
    assert T.generate("DEF5GH", 18463 * DAY, serial) == expected


def test_official_control_string():
    assert T.control_string("DEF5GH", 18463, 12) == "68697057172018463000000000012"


@pytest.mark.parametrize("taxid", REAL_ACCEPTED + [e for _, e in OFFICIAL])


def test_validate_accepts_known_good(taxid):
    res = T.validate(taxid)
    assert res["ok"], res


def test_verhoeff_official_sdk_unit_test():
    assert T.verhoeff_check_digit("123") == 3
    assert T.verhoeff_is_valid("1233")


def test_lowercase_memory_id_is_uppercased_first():
    assert T.generate("def5gh", 18463 * DAY, 12) == "DEF5GH0481F000000000C2"


def test_bad_check_digit_detected():
    res = T.validate("DEF5GH0481F000000000C7")  # what moadian-full 0.0.2 produces
    assert not res["ok"]
    assert "expected 2" in res["errors"][0]


def test_wrong_length():
    res = T.validate("DEF5GH0481F")
    assert not res["ok"] and "length" in res["errors"][0]


def test_non_hex_serial():
    res = T.validate("DEF5GH0481FZZZZZZZZZZ2")
    assert not res["ok"]


def test_indatim_day_mismatch():
    res = T.validate("DEF5GH0481F000000000C2", indatim_ms=18464 * DAY + 5)
    assert not res["ok"] and "indatim" in res["errors"][0]


def test_indatim_same_day_ok():
    assert T.validate("DEF5GH0481F000000000C2", indatim_ms=18463 * DAY + DAY - 1)["ok"]


def test_inno_mismatch_is_warning():
    res = T.validate("DEF5GH0481F000000000C2", inno="12")
    assert res["ok"] and res["warnings"]


def test_forbidden_memory_id_chars_warn():
    t = T.generate("ABCDE0", 18463 * DAY, 1)  # B, C reserved; 0 forbidden
    res = T.validate(t)
    assert res["ok"] and res["warnings"]


def test_decode():
    d = T.decode("DEF5GH0481F000000000C2")
    assert d["days_since_epoch"] == 18463 and d["date_utc"] == "2020-07-20"
    assert d["serial"] == 12 and d["inno_expected"] == "000000000C"


def test_persian_digits_rejected():
    fa = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")
    t = "DEF5GH0481F000000000C2"
    assert "hexadecimal" in T.decode(t[:6] + t[6:21].translate(fa) + t[21])["error"]
    assert not T.validate(t[:-1] + t[-1].translate(fa))["ok"]
    with pytest.raises(ValueError, match="Latin"):
        T.generate("A1121" + "6".translate(fa), 18463 * DAY, 1)


def test_serial_out_of_range():
    with pytest.raises(ValueError):
        T.generate("A11216", 0, 16**10)


def test_cli_generate(capsys):
    assert T.main(["generate", "--memory-id", "A11216", "--date", "2023-05-01T00:00:00Z", "--serial", "1"]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["taxid"] == "A1121604C1600000000019" and out["inno"] == "0000000001"


def test_cli_validate_fails_with_exit_1(capsys):
    assert T.main(["validate", "DEF5GH0481F000000000C7"]) == 1


def test_cli_rejects_naive_date(capsys):
    assert T.main(["generate", "--memory-id", "A11216", "--date", "2023-05-01T00:00:00", "--serial", "1"]) == 1
