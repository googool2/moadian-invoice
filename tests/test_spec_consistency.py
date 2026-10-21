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
