#!/usr/bin/env python3
"""Send a validated invoice to the Moadian system — two-step, explicit confirmation.

    # 1. offline: validate, show a summary and get a confirmation code (no network, no key)
    python scripts/send_invoice.py prepare invoice.json --target sandbox
    # 2. only after the user has read the summary and said "send it":
    python scripts/send_invoice.py send invoice.json --target sandbox --confirm 7F3A-91C2-04
    # read-only calls
    python scripts/send_invoice.py inquiry --target sandbox --uid <uid> [--uid ...]
    python scripts/send_invoice.py fiscal-info --target sandbox

Secrets come only from environment variables, never from arguments or files in a repo:
    MOADIAN_MEMORY_ID              6-char memory id (شناسه یکتای حافظه مالیاتی)
    MOADIAN_PRIVATE_KEY_PATH       PEM private key, outside any git repository
    MOADIAN_CERT_PATH              PEM certificate (-----BEGIN CERTIFICATE-----)
    MOADIAN_PRIVATE_KEY_PASSWORD   optional, for an encrypted key (decrypted in memory only)
    MOADIAN_SANDBOX_BASE_URL       required for --target sandbox (no sandbox URL is in the official
                                   spec; secondary sources name host sandboxrc.tax.gov.ir) [UNVERIFIED]
    MOADIAN_ALLOW_LIVE=1           required for --target live; set it yourself, in your own shell

Live base URL: https://tp.tax.gov.ir/requestsmanager/api/v2/ (RC_TICS.IS v1.6).

Uses moadian-full's client, with these send-path defects fixed at run time (the installed
library is not modified): the JWS `sigT` time was frozen at import; the tax system's public
key was cached forever in the shared temp dir (mixing sandbox and live); URLs were fixed to
live; encrypted private keys were unsupported. A receipt per taxid is kept in
~/.moadian-invoice/receipts/ and a taxid that already has a receipt is never sent again.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse



def _invoice_scripts() -> Path:
    """This skill reuses the validator from its sibling skill `moadian-invoice`
    (installed next to it: plugin skills/ folder or ~/.claude/skills/)."""
    env = os.environ.get("MOADIAN_INVOICE_SCRIPTS")
    candidates = [Path(env)] if env else []
    candidates.append(Path(__file__).resolve().parents[2] / "moadian-invoice" / "scripts")
    for c in candidates:
        if (c / "validate_invoice.py").exists():
            return c
    sys.exit(json.dumps({"ok": False, "error": "the moadian-invoice skill was not found next to moadian-send; "
                         "install both, or set MOADIAN_INVOICE_SCRIPTS to its scripts folder"}))


sys.path.insert(0, str(_invoice_scripts()))
import _cli  # noqa: E402
import _moadian  # noqa: E402
import validate_invoice  # noqa: E402

LIVE_BASE = "https://tp.tax.gov.ir/requestsmanager/api/v2/"
ENDPOINTS = {"NONCE_URL": "nonce", "SERVER_INFORMATION_URL": "server-information",
             "FISCAL_INFORMATION_URL": "fiscal-information", "TAXPAYER_URL": "taxpayer",
             "INVOICE_URL": "invoice", "INQUIRY_URL": "inquiry",
             "INQUIRY_BY_REFERENCE_ID_URL": "inquiry-by-reference-id", "INQUIRY_BY_UID_URL": "inquiry-by-uid"}
EXIT_OK, EXIT_INVALID, EXIT_REFUSED, EXIT_NEEDS_CONFIRM, EXIT_NETWORK = 0, 1, 2, 3, 4


class Refused(Exception):
    """A safety rule stopped the command. Nothing was sent."""


def state_dir() -> Path:
    return Path(os.environ.get("MOADIAN_STATE_DIR") or Path.home() / ".moadian-invoice")


def base_url(target: str) -> str:
    if target == "live":
        return LIVE_BASE
    url = os.environ.get("MOADIAN_SANDBOX_BASE_URL", "").strip()
    if not url:
        raise Refused("set MOADIAN_SANDBOX_BASE_URL to the sandbox API base URL your trusted company / INTA "
                      "gave you (the official spec has no sandbox URL)")
    if urlparse(url).scheme != "https":
        raise Refused("MOADIAN_SANDBOX_BASE_URL must be an https URL")
    return url if url.endswith("/") else url + "/"


def confirmation_code(invoice: dict, target: str, url: str) -> str:
    canonical = json.dumps(invoice, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(f"{canonical}|{target}|{url}".encode()).hexdigest()[:10].upper()
    return f"{digest[:4]}-{digest[4:8]}-{digest[8:]}"


def receipt_path(taxid: str) -> Path:
    return state_dir() / "receipts" / f"{taxid}.json"


def prepare(path: str, target: str) -> dict:
    """Offline checks + summary + confirmation code. Never touches the network or a key."""
    invoice = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(invoice, dict):
        raise Refused("the file is not an invoice object (expected {header, body, payments})")
    now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    check = validate_invoice.validate(invoice, now_ms)
    h = invoice.get("header") if isinstance(invoice.get("header"), dict) else {}
    url = base_url(target)
    out = {
        "ok": check["ok"], "target": target, "base_url": url,
        "summary": {"taxid": h.get("taxid"), "inty": h.get("inty"), "inp": h.get("inp"), "ins": h.get("ins"),
                    "seller": h.get("tins"), "buyer": h.get("tinb") or h.get("bid"), "lines": len(invoice.get("body") or []),
                    "tbill": h.get("tbill"), "indatim_utc": _iso(h.get("indatim"))},
        "errors": check["errors"], "warnings": check["warnings"],
    }
    late = [w for w in check["warnings"] if w.get("rule") == "R21"]
    if late:  # S1 §7-2: send within one week. The validator only warns; for sending it blocks.
        out["ok"] = False
        out["errors"].append({"path": "header.indatim", "message": "invoice is more than one week old; S1 §7-2 "
                              "requires sending within a week — check with the user/accountant before going on"})
    if h.get("taxid") and receipt_path(h["taxid"]).exists():
        out["ok"] = False
        out["errors"].append({"path": "header.taxid", "message": "this taxid was already sent (receipt exists); a "
                              "resent taxid is rejected with 0300101 — build a new invoice with a new serial"})
    if out["ok"]:
        out["confirmation_code"] = confirmation_code(invoice, target, url)
        out["next_step"] = ("Show this summary to the user. Only if they explicitly say to send THIS invoice to "
                            f"{target}, run: send {path} --target {target} --confirm {out['confirmation_code']}")
    return out


def _iso(ms):
    if not isinstance(ms, int):
        return None
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).isoformat()


def _inside_git_repo(p: Path) -> bool:
    return any((parent / ".git").exists() for parent in [p.parent, *p.parent.parents])


def load_credentials() -> tuple[str, bytes, bytes]:
    names = ("MOADIAN_MEMORY_ID", "MOADIAN_PRIVATE_KEY_PATH", "MOADIAN_CERT_PATH")
    missing = [n for n in names if not os.environ.get(n)]
    if missing:
        raise Refused("missing environment variables: " + ", ".join(missing) + " (never pass keys as arguments)")
    key_path = Path(os.environ["MOADIAN_PRIVATE_KEY_PATH"]).expanduser().resolve()
    cert_path = Path(os.environ["MOADIAN_CERT_PATH"]).expanduser().resolve()
    if _inside_git_repo(key_path):
        raise Refused(f"the private key is inside a git repository ({key_path.parent}); move it out first")
    key_pem, cert_pem = key_path.read_bytes(), cert_path.read_bytes()
    if b"BEGIN CERTIFICATE" not in cert_pem:
        raise Refused("MOADIAN_CERT_PATH is not a PEM certificate (a CSR does not work)")
    password = os.environ.get("MOADIAN_PRIVATE_KEY_PASSWORD")
    if password:  # the library only takes unencrypted PEM; decrypt in memory, never write it out
        from cryptography.hazmat.primitives import serialization

        key = serialization.load_pem_private_key(key_pem, password=password.encode())
        key_pem = key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                                    serialization.NoEncryption())
    return os.environ["MOADIAN_MEMORY_ID"].strip().upper(), key_pem, cert_pem


def make_client(target: str):
    """moadian-full's Moadian client with the send-path fixes applied."""
    _moadian.load()
    main = importlib.import_module(f"{_moadian._PKG}.main")
    enc = importlib.import_module(f"{_moadian._PKG}.encryption")
    url = base_url(target)
    for const, path in ENDPOINTS.items():  # fix: URLs were hard-coded to live
        setattr(main, const, url + path)
    if not getattr(main, "_moadian_invoice_patched", False):
        original_sign = enc.sign

        def sign_fresh(payload, key, cert):  # fix: sigT was computed once, at import time
            enc.__dict__["__signature_time"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            return original_sign(payload, key, cert)

        main.sign = sign_fresh
        main._moadian_invoice_patched = True
    memory_id, key_pem, cert_pem = load_credentials()
    client = main.Moadian(memory_id, key_pem, cert_pem, storage_path=str(state_dir()))
    cache: dict = {}

    def server_key():  # fix: key was cached forever in the shared temp dir, across sandbox and live
        if "key" not in cache:
            info = client._send_http_request(main.SERVER_INFORMATION_URL, need_token=True)
            keys = info.get("publicKeys") or []
            if not keys:
                raise RuntimeError("server-information returned no public key")
            cache["key"] = keys[0]
        return cache["key"]

    client._get_tax_gov_key = server_key
    return client


def send(path: str, target: str, confirm: str | None) -> tuple[int, dict]:
    prep = prepare(path, target)
    if not prep["ok"]:
        return EXIT_INVALID, {**prep, "sent": False}
    if not confirm:
        return EXIT_NEEDS_CONFIRM, {**prep, "sent": False,
                                    "message": "not sent: confirmation required (see next_step)"}
    if confirm.strip().upper() != prep["confirmation_code"]:
        raise Refused("confirmation code does not match this invoice and target — the file or target changed "
                      "since prepare; run prepare again and re-confirm with the user")
    if target == "live" and os.environ.get("MOADIAN_ALLOW_LIVE") != "1":
        raise Refused("live sending needs MOADIAN_ALLOW_LIVE=1, set by the user in their own shell")
    invoice = json.loads(Path(path).read_text(encoding="utf-8"))
    client = make_client(target)
    response = client.send_invoice(json.dumps(invoice, ensure_ascii=False))
    first = (response.get("result") or [{}])[0] if isinstance(response, dict) else {}
    receipt = {"taxid": invoice["header"]["taxid"], "target": target, "base_url": prep["base_url"],
               "sent_at": datetime.now(timezone.utc).isoformat(), "uid": first.get("uid"),
               "reference_number": first.get("referenceNumber"), "response": response}
    rp = receipt_path(receipt["taxid"])
    rp.parent.mkdir(parents=True, exist_ok=True)
    rp.write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding="utf-8")
    return EXIT_OK, {"ok": True, "sent": True, "target": target, "uid": receipt["uid"],
                     "reference_number": receipt["reference_number"], "receipt": str(rp),
                     "next_step": "processing is asynchronous: run inquiry --uid later; on FAILED use explain_error.py "
                                  "--from-response"}


def main(argv: list[str] | None = None) -> int:
    _cli.setup_stdout()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    _cli.add_version(ap, "send_invoice")
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("prepare", "send"):
        p = sub.add_parser(name)
        p.add_argument("file")
        p.add_argument("--target", choices=("sandbox", "live"), required=True)
        if name == "send":
            p.add_argument("--confirm", help="code printed by prepare, after the user's explicit OK")
    q = sub.add_parser("inquiry", help="read-only status lookup")
    q.add_argument("--target", choices=("sandbox", "live"), required=True)
    q.add_argument("--uid", action="append", default=[])
    q.add_argument("--reference-id", action="append", default=[])
    f = sub.add_parser("fiscal-info", help="read-only check of the memory id (connection test)")
    f.add_argument("--target", choices=("sandbox", "live"), required=True)
    args = ap.parse_args(argv)
    try:
        if args.cmd == "prepare":
            out = prepare(args.file, args.target)
            code = EXIT_OK if out["ok"] else EXIT_INVALID
        elif args.cmd == "send":
            code, out = send(args.file, args.target, args.confirm)
        elif args.cmd == "inquiry":
            if not (args.uid or args.reference_id):
                raise Refused("give --uid or --reference-id")
            client = make_client(args.target)
            out = {"ok": True, "by_uid": client.inquiry_by_uid(args.uid) if args.uid else None,
                   "by_reference_id": client.inquiry_by_reference_id(args.reference_id) if args.reference_id else None}
            code = EXIT_OK
        else:
            out, code = {"ok": True, "fiscal_information": make_client(args.target).get_fiscal_information()}, EXIT_OK
    except Refused as exc:
        out, code = {"ok": False, "sent": False, "refused": str(exc)}, EXIT_REFUSED
    except (_moadian.MoadianFullMissing, FileNotFoundError, ValueError) as exc:
        out, code = {"ok": False, "sent": False, "error": f"{type(exc).__name__}: {exc}"}, EXIT_REFUSED
    except Exception as exc:  # network / server errors from the client; nothing is retried automatically
        out, code = {"ok": False, "error": f"{type(exc).__name__}: {exc}",
                     "note": "if this happened during send, check inquiry before resending: the server may "
                             "have registered the invoice"}, EXIT_NETWORK
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return code


if __name__ == "__main__":
    sys.exit(main())
