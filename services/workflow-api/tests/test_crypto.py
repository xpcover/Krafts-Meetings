import pytest

from app.crypto import TokenCipher


def test_token_cipher_round_trip_without_plaintext_leak():
    key = TokenCipher.generate_key()
    cipher = TokenCipher(key)

    encrypted = cipher.encrypt("refresh-token-secret")

    assert encrypted != "refresh-token-secret"
    assert "refresh-token-secret" not in encrypted
    assert cipher.decrypt(encrypted) == "refresh-token-secret"


def test_token_cipher_rejects_missing_key():
    with pytest.raises(ValueError, match="WORKFLOW_ENCRYPTION_KEY"):
        TokenCipher("")


def test_token_cipher_rejects_invalid_ciphertext():
    cipher = TokenCipher(TokenCipher.generate_key())

    with pytest.raises(ValueError, match="Invalid encrypted token"):
        cipher.decrypt("not-a-fernet-token")
