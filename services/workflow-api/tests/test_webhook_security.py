import hashlib
import hmac
import time

from app.webhook_security import verify_vexa_signature


def _signature(secret: str, timestamp: str, body: bytes) -> str:
    signed = f"{timestamp}.".encode("utf-8") + body
    return "sha256=" + hmac.new(secret.encode("utf-8"), signed, hashlib.sha256).hexdigest()


def test_verify_vexa_signature_accepts_valid_signature():
    body = b'{"event_type":"meeting.completed"}'
    timestamp = str(int(time.time()))
    signature = _signature("secret", timestamp, body)

    assert verify_vexa_signature(body, "secret", signature, timestamp)


def test_verify_vexa_signature_rejects_tampered_body():
    body = b'{"event_type":"meeting.completed"}'
    timestamp = str(int(time.time()))
    signature = _signature("secret", timestamp, body)

    assert not verify_vexa_signature(b'{"event_type":"meeting.started"}', "secret", signature, timestamp)


def test_verify_vexa_signature_rejects_old_timestamp():
    body = b"{}"
    timestamp = str(int(time.time()) - 1000)
    signature = _signature("secret", timestamp, body)

    assert not verify_vexa_signature(body, "secret", signature, timestamp, tolerance_seconds=300)
