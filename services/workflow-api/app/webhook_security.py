"""Webhook signature verification helpers."""

import hashlib
import hmac
import time


def verify_vexa_signature(
    body: bytes,
    secret: str,
    signature: str | None,
    timestamp: str | None,
    tolerance_seconds: int = 300,
) -> bool:
    if not secret or not signature or not timestamp:
        return False
    try:
        ts = int(timestamp)
    except ValueError:
        return False
    if abs(int(time.time()) - ts) > tolerance_seconds:
        return False

    signed_content = f"{ts}.".encode("utf-8") + body
    expected = "sha256=" + hmac.new(secret.encode("utf-8"), signed_content, hashlib.sha256).hexdigest()
    return hmac.compare_digest(signature, expected)
