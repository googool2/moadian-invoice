import pytest

import _mini_yaml as y


def test_nested_map_and_list_of_maps():
    doc = y.loads(
        """
seller_tin: "10101234565"   # comment
buyer:
  tin: "14011576540"
  type: 1
items:
  - sstid: "2330004219206"
    sstt: پرینتر
    fee: 120000000
    am: 2
  - sstid: "2330004219207"
    fee: 1.5
"""
    )
    assert doc["seller_tin"] == "10101234565"
    assert doc["buyer"] == {"tin": "14011576540", "type": 1}
    assert doc["items"][0]["sstt"] == "پرینتر"
    assert doc["items"][0]["am"] == 2
    assert doc["items"][1]["fee"] == 1.5


def test_leading_zero_numbers_stay_strings():
    # PyYAML would read 0300101 as octal 98369; we must not.
    doc = y.loads("code: 0300101\ntin: 0012345678\nzero: 0\nneg: -5")
    assert doc == {"code": "0300101", "tin": "0012345678", "zero": 0, "neg": -5}


def test_booleans_and_null():
    assert y.loads("a: true\nb: false\nc: null\nd:") == {"a": True, "b": False, "c": None, "d": None}


def test_scalar_list():
    assert y.loads("x:\n  - a\n  - 2") == {"x": ["a", 2]}


def test_flow_style_rejected():
    with pytest.raises(ValueError):
        y.loads("a: {b: 1}")


def test_bad_indent_rejected():
    with pytest.raises(ValueError):
        y.loads("a: 1\n   b: 2")


def test_persian_digits_stay_strings():
    # YAML integers are 0-9 only; Persian digits must reach the validator as text
    assert y.loads("sstid: ۲۳۳۰۰۰۴۲۱۹۲۰۶\n") == {"sstid": "۲۳۳۰۰۰۴۲۱۹۲۰۶"}
