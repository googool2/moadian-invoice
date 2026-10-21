"""Release hygiene: one version everywhere, --version on every CLI, UTF-8 output on any OS."""
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

import _cli

ROOT = Path(__file__).resolve().parent.parent
CLIS = [ROOT / "skills/moadian-invoice/scripts" / n for n in
        ("validate_invoice.py", "build_invoice.py", "taxid.py", "explain_error.py")] + \
       [ROOT / "skills/moadian-send/scripts/send_invoice.py"]


def test_versions_consistent():
    plugin = json.loads((ROOT / ".claude-plugin/plugin.json").read_text(encoding="utf-8"))
    market = json.loads((ROOT / ".claude-plugin/marketplace.json").read_text(encoding="utf-8"))
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    assert plugin["version"] == _cli.VERSION
    assert market["metadata"]["version"] == _cli.VERSION
    assert all(p["version"] == _cli.VERSION for p in market["plugins"])
    assert re.search(rf"^## \[{re.escape(_cli.VERSION)}\]", changelog, re.M)


def _run(script, *args, encoding=None):
    env = dict(os.environ)
    if encoding:
        env["PYTHONIOENCODING"] = encoding
    return subprocess.run([sys.executable, str(script), *args], capture_output=True, env=env)


@pytest.mark.parametrize("script", CLIS, ids=lambda p: p.name)
def test_version_flag(script):
    res = _run(script, "--version")
    assert res.returncode == 0 and res.stdout.decode().strip().endswith(_cli.VERSION)


@pytest.mark.parametrize("args", [
    ("explain_error.py", "0300101"),
    ("validate_invoice.py", str(ROOT / "skills/moadian-invoice/examples/invoice-type1-minimal.json")),
    ("taxid.py", "decode", "DEF5GH0481F000000000C2"),
])
def test_persian_output_survives_a_windows_code_page(args):
    res = _run(ROOT / "skills/moadian-invoice/scripts" / args[0], *args[1:], encoding="cp1252")
    assert res.returncode == 0, res.stderr.decode(errors="replace")
    json.loads(res.stdout.decode("utf-8"))


def test_send_finds_sibling_skill_from_its_own_folder():
    res = _run(CLIS[-1], "--version")
    assert res.returncode == 0
