"""Keep the human-readable references and the validator's spec in sync."""
import re
from pathlib import Path

import _spec as spec

REF = Path(__file__).resolve().parent.parent / "skills" / "moadian-invoice" / "references"


def test_invoice_types_matrix_matches_spec():
    text = (REF / "invoice-types.md").read_text(encoding="utf-8")
    rows = {}
    for line in text.splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) == 2 + len(spec.MATRIX_COLUMNS) and re.fullmatch(r"[a-z0-9]+", cells[0]) and cells[0] != "field":
            rows[cells[0]] = "".join("-" if c == "–" else c for c in cells[2:])
    assert rows.keys() == spec.MATRIX.keys()
    for field, status in spec.MATRIX.items():
        assert rows[field] == status.replace("/", ""), field


def test_every_spec_field_is_documented():
    text = (REF / "fields.md").read_text(encoding="utf-8")
    for field in spec.FIELDS:
        assert re.search(rf"(^\| |, |\(){re.escape(field)}\b", text, re.M), field


def test_enums_documented():
    text = (REF / "invoice-types.md").read_text(encoding="utf-8")
    for inp, name in spec.ENUMS["inp"].items():
        assert f"| {inp} | {name}" in text, (inp, name)


def test_reference_files_have_no_todo():
    for f in REF.glob("*.md"):
        assert "TODO" not in f.read_text(encoding="utf-8"), f


def test_unit_list_is_complete_and_well_formed():
    units = spec.units()
    text = (REF / "units.md").read_text(encoding="utf-8")
    rows = [int(r) for r in re.findall(r"^\| \d+ \| [^|]+ \| [^|]+ \| (\d+) \|$", text, re.M)]
    assert rows == list(range(1, 103))                      # RC_UMGS.ST_V1.18 has 102 rows, none skipped
    assert len(units) == 102                                # and 102 distinct codes
    assert all(c.isascii() and c.isdigit() and len(c) <= 8 for c in units)  # fits mu's N<=8
    assert spec.FIELDS["mu"][1] == "N<=8"
    assert {units["1627"], units["164"], units["16134"]} == {"عدد", "کیلوگرم", "نفر-ماه"}
    assert not any(ch in name for name in units.values() for ch in "كي")  # Persian, not Arabic, letters


def test_unit_list_source_hash_matches_fields_md():
    full = re.search(r"sha256 `([0-9a-f]{64})`", (REF / "units.md").read_text(encoding="utf-8")).group(1)
    s4 = re.search(r"^\| S4 \|.*?sha256 starts `([0-9a-f]{8})`, ends `([0-9a-f]{4})`",
                   (REF / "fields.md").read_text(encoding="utf-8"), re.M)
    assert full.startswith(s4.group(1)) and full.endswith(s4.group(2))
