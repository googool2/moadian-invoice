"""Load the offline parts of the `moadian-full` package.

Why this exists: `pip install moadian-full` (v0.0.2) installs its code in a
folder literally named `moadian-full` (with a hyphen), so the documented
`import moadian_full` raises ModuleNotFoundError. Its `__init__` also imports
the HTTP client (requests, authlib, cryptography) and monkey-patches authlib.

This helper registers that folder as a synthetic package and imports only the
offline submodules (invoice_builder, tax_id, serial_manager, verhoeff). It
never imports `main.py`, so nothing here can reach the network.
"""

from __future__ import annotations

import importlib
import importlib.util
import sys
import types
from pathlib import Path

_PKG = "_moadian_full_offline"
_SUBMODULES = ("verhoeff", "tax_id", "serial_manager", "invoice_builder")


class MoadianFullMissing(RuntimeError):
    """Raised when moadian-full is not installed."""


def _find_package_dir() -> Path:
    # Newer releases may fix the folder name; prefer a real module if present.
    spec = importlib.util.find_spec("moadian_full")
    if spec and spec.submodule_search_locations:
        return Path(list(spec.submodule_search_locations)[0])
    try:
        from importlib import metadata

        dist = metadata.distribution("moadian-full")
    except Exception as exc:  # PackageNotFoundError and friends
        raise MoadianFullMissing(
            "moadian-full is not installed. Run: pip install moadian-full"
        ) from exc
    for f in dist.files or []:
        parts = Path(str(f)).parts
        if len(parts) == 2 and parts[1] == "invoice_builder.py":
            return Path(str(dist.locate_file(f))).parent
    raise MoadianFullMissing("moadian-full is installed but invoice_builder.py was not found")


def load() -> types.SimpleNamespace:
    """Return a namespace with InvoiceBuilder, InvoiceItem, TaxIdGenerator,
    SerialManager, Verhoeff and the package version."""
    if _PKG not in sys.modules:
        pkg_dir = _find_package_dir()
        pkg = types.ModuleType(_PKG)
        pkg.__path__ = [str(pkg_dir)]  # makes relative imports inside it work
        sys.modules[_PKG] = pkg
    mods = {name: importlib.import_module(f"{_PKG}.{name}") for name in _SUBMODULES}
    try:
        from importlib import metadata

        version = metadata.version("moadian-full")
    except Exception:
        version = "unknown"
    return types.SimpleNamespace(
        InvoiceBuilder=mods["invoice_builder"].InvoiceBuilder,
        InvoiceItem=mods["invoice_builder"].InvoiceItem,
        TaxIdGenerator=mods["tax_id"].TaxIdGenerator,
        SerialManager=mods["serial_manager"].SerialManager,
        Verhoeff=mods["verhoeff"].Verhoeff,
        version=version,
    )
