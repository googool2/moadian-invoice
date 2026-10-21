"""send_invoice.py against a fake tax server — no real network, throw-away test keys."""
import base64
import importlib
import json
from datetime import datetime, timedelta, timezone

import pytest

import _moadian
import build_invoice as B
import send_invoice as S

try:
    _moadian.load()
    import requests
    from authlib.jose import JsonWebEncryption, JsonWebSignature  # moadian-full's own (deprecated) JOSE lib
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.x509.oid import NameOID
except Exception:  # pragma: no cover
    pytest.skip("moadian-full and its dependencies are needed", allow_module_level=True)

SANDBOX = "https://sandbox.example.tax.gov.ir/requestsmanager/api/v2/"


def _keypair():
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


@pytest.fixture(scope="module")
def client_keys():
    key = _keypair()
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "test")])
    now = datetime.now(timezone.utc)
    cert = (x509.CertificateBuilder().subject_name(name).issuer_name(name).public_key(key.public_key())
            .serial_number(1).not_valid_before(now - timedelta(days=1)).not_valid_after(now + timedelta(days=1))
            .sign(key, hashes.SHA256()))
    return key, cert


@pytest.fixture
def env(tmp_path, monkeypatch, client_keys):
    """Keys outside any git repo, sandbox URL, private state dir, temp dir redirected."""
    key, cert = client_keys
    secrets = tmp_path / "secrets"
    secrets.mkdir()
    (secrets / "key.pem").write_bytes(key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                                                        serialization.NoEncryption()))
    (secrets / "cert.pem").write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    monkeypatch.setenv("MOADIAN_MEMORY_ID", "A11216")
    monkeypatch.setenv("MOADIAN_PRIVATE_KEY_PATH", str(secrets / "key.pem"))
    monkeypatch.setenv("MOADIAN_CERT_PATH", str(secrets / "cert.pem"))
    monkeypatch.setenv("MOADIAN_SANDBOX_BASE_URL", SANDBOX)
    monkeypatch.setenv("MOADIAN_STATE_DIR", str(tmp_path / "state"))
    monkeypatch.delenv("MOADIAN_ALLOW_LIVE", raising=False)
    monkeypatch.delenv("MOADIAN_PRIVATE_KEY_PASSWORD", raising=False)
    monkeypatch.setattr("tempfile.tempdir", str(tmp_path / "tmp"))
    (tmp_path / "tmp").mkdir()
    return tmp_path


@pytest.fixture
def no_network(monkeypatch):
    def boom(*a, **k):
        raise AssertionError("network used")
    monkeypatch.setattr(requests, "request", boom)


@pytest.fixture
def fresh_invoice(env):
    spec = {"memory_id": "A11216", "seller_tin": "10101234565", "type": 1, "pattern": 1, "subject": 1,
            "indatim": int(datetime.now(timezone.utc).timestamp() * 1000) - 60_000, "serial": 4242,
            "buyer": {"type": 2, "tin": "14011576540"},
            "items": [{"sstid": "2330004219206", "quantity": 1, "unit_price": 1000000, "vat_rate": 10}]}
    inv = B.build(spec, state_dir=str(env / "state"))["invoice"]
    path = env / "invoice.json"
    path.write_text(json.dumps(inv, ensure_ascii=False), encoding="utf-8")
    return path, inv


class FakeServer:
    def __init__(self):
        self.key = _keypair()
        der = self.key.public_key().public_bytes(serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo)
        self.public_b64 = base64.b64encode(der).decode()
        self.calls, self.packets = [], []

    def __call__(self, method, url, headers=None, timeout=None, **kw):
        self.calls.append((method.upper(), url))
        assert url.startswith(SANDBOX), url
        endpoint = url[len(SANDBOX):]
        if endpoint == "nonce":
            body = {"nonce": "n-123"}
        elif endpoint == "server-information":
            body = {"publicKeys": [{"key": self.public_b64, "id": "k1"}]}
        elif endpoint == "invoice":
            self.packets += json.loads(kw["data"])
            body = {"result": [{"uid": "uid-1", "referenceNumber": "ref-1"}]}
        elif endpoint == "inquiry-by-uid":
            body = [{"uid": "uid-1", "status": "SUCCESS"}]
        else:
            body = {"endpoint": endpoint}
        return _Resp(body)


class _Resp:
    status_code, text = 200, ""

    def __init__(self, body):
        self._body = body

    def raise_for_status(self):
        pass

    def json(self):
        return self._body


def test_prepare_is_offline_and_deterministic(fresh_invoice, no_network):
    path, _ = fresh_invoice
    a, b = S.prepare(str(path), "sandbox"), S.prepare(str(path), "sandbox")
    assert a["ok"] and a["confirmation_code"] == b["confirmation_code"]
    assert S.prepare(str(path), "live")["confirmation_code"] != a["confirmation_code"]  # bound to target


def test_prepare_refuses_invalid_and_stale(env, no_network):
    from pathlib import Path

    ex = Path(__file__).resolve().parent.parent / "examples"
    assert not S.prepare(str(ex / "invoice-invalid-arith.json"), "sandbox")["ok"]
    stale = S.prepare(str(ex / "invoice-type1-minimal.json"), "sandbox")  # dated 1405-02-01
    assert not stale["ok"] and "confirmation_code" not in stale


def test_send_without_confirmation_does_not_send(fresh_invoice, no_network):
    code, out = S.send(str(fresh_invoice[0]), "sandbox", None)
    assert code == S.EXIT_NEEDS_CONFIRM and out["sent"] is False and out["confirmation_code"]


def test_wrong_or_stale_code_refused(fresh_invoice, no_network):
    path, inv = fresh_invoice
    good = S.prepare(str(path), "sandbox")["confirmation_code"]
    with pytest.raises(S.Refused):
        S.send(str(path), "sandbox", "0000-0000-00")
    inv["header"]["sbc"] = "0001"  # file changed after the user confirmed
    path.write_text(json.dumps(inv), encoding="utf-8")
    with pytest.raises(S.Refused):
        S.send(str(path), "sandbox", good)


def test_live_needs_user_set_flag(fresh_invoice, no_network):
    path, _ = fresh_invoice
    code = S.prepare(str(path), "live")["confirmation_code"]
    with pytest.raises(S.Refused, match="MOADIAN_ALLOW_LIVE"):
        S.send(str(path), "live", code)


def test_sandbox_url_required_and_https(fresh_invoice, monkeypatch, no_network):
    monkeypatch.delenv("MOADIAN_SANDBOX_BASE_URL")
    with pytest.raises(S.Refused):
        S.prepare(str(fresh_invoice[0]), "sandbox")
    monkeypatch.setenv("MOADIAN_SANDBOX_BASE_URL", "http://insecure.example/")
    with pytest.raises(S.Refused):
        S.prepare(str(fresh_invoice[0]), "sandbox")


def test_missing_env_and_key_in_repo_refused(fresh_invoice, env, monkeypatch, no_network):
    path, _ = fresh_invoice
    code = S.prepare(str(path), "sandbox")["confirmation_code"]
    monkeypatch.delenv("MOADIAN_CERT_PATH")
    with pytest.raises(S.Refused, match="MOADIAN_CERT_PATH"):
        S.send(str(path), "sandbox", code)
    monkeypatch.setenv("MOADIAN_CERT_PATH", str(env / "secrets" / "cert.pem"))
    (env / "secrets" / ".git").mkdir()  # pretend the key folder is a repository
    with pytest.raises(S.Refused, match="git repository"):
        S.send(str(path), "sandbox", code)


def test_full_send_with_fake_server(fresh_invoice, env, monkeypatch, client_keys):
    path, inv = fresh_invoice
    server = FakeServer()
    monkeypatch.setattr(requests, "request", server)
    enc = importlib.import_module(f"{_moadian._PKG}.encryption")
    monkeypatch.setitem(enc.__dict__, "__signature_time", "2000-01-01T00:00:00Z")  # stale, as after a long uptime

    code = S.prepare(str(path), "sandbox")["confirmation_code"]
    rc, out = S.send(str(path), "sandbox", code)
    assert rc == S.EXIT_OK and out["sent"] and out["uid"] == "uid-1" and out["reference_number"] == "ref-1"
    assert ("POST", SANDBOX + "invoice") in server.calls
    assert not any(u.startswith("https://tp.tax.gov.ir") for _, u in server.calls)  # stayed on the sandbox

    # the packet decrypts with the server key and carries a fresh sigT signed by the client key
    packet = server.packets[0]
    assert packet["header"]["fiscalId"] == "A11216"
    jws_compact = JsonWebEncryption().deserialize_compact(packet["payload"], server.key)["payload"]
    signed = JsonWebSignature().deserialize_compact(jws_compact, client_keys[0].public_key())
    sig_t = datetime.strptime(signed["header"]["sigT"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    assert abs((datetime.now(timezone.utc) - sig_t).total_seconds()) < 120
    assert json.loads(signed["payload"]) == inv

    # nothing was cached in the shared temp dir, and the receipt blocks a second send of the same taxid
    assert not (env / "tmp" / "tax_gov_key").exists()
    assert S.receipt_path(inv["header"]["taxid"]).exists()
    again = S.prepare(str(path), "sandbox")
    assert not again["ok"] and "already sent" in again["errors"][-1]["message"]


def test_encrypted_key_is_decrypted_in_memory(fresh_invoice, env, monkeypatch, client_keys):
    key, _ = client_keys
    enc_pem = key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                                serialization.BestAvailableEncryption(b"s3cret"))
    (env / "secrets" / "key.pem").write_bytes(enc_pem)
    monkeypatch.setenv("MOADIAN_PRIVATE_KEY_PASSWORD", "s3cret")
    memory_id, key_pem, _ = S.load_credentials()
    assert memory_id == "A11216" and b"ENCRYPTED" not in key_pem
    assert (env / "secrets" / "key.pem").read_bytes() == enc_pem  # file untouched


def test_inquiry_cli(env, monkeypatch, capsys):
    server = FakeServer()
    monkeypatch.setattr(requests, "request", server)
    assert S.main(["inquiry", "--target", "sandbox", "--uid", "uid-1"]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["by_uid"][0]["status"] == "SUCCESS"


def test_cli_refusal_exit_code(env, monkeypatch, capsys, no_network):
    monkeypatch.delenv("MOADIAN_SANDBOX_BASE_URL")
    assert S.main(["fiscal-info", "--target", "sandbox"]) == S.EXIT_REFUSED
    assert "refused" in json.loads(capsys.readouterr().out)


def test_non_object_file_refused(env, capsys, no_network):
    bad = env / "list.json"
    bad.write_text("[]", encoding="utf-8")
    assert S.main(["prepare", str(bad), "--target", "sandbox"]) == S.EXIT_REFUSED
