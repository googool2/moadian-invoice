"""Shared CLI pieces: one version number for every script, UTF-8 output on every OS.

Windows pipes default to the locale code page (e.g. cp1252), so printing Persian text
crashed with UnicodeEncodeError before this. The version is kept in sync with
.claude-plugin/plugin.json, marketplace.json and CHANGELOG.md by tests/test_release.py.
"""

from __future__ import annotations

import sys

VERSION = "0.3.0"


def setup_stdout() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass  # replaced or already-detached streams (e.g. under pytest capture)


def add_version(parser, prog: str) -> None:
    parser.add_argument("--version", action="version", version=f"{prog} {VERSION}")
