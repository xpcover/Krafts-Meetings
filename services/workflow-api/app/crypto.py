"""Encryption helpers for OAuth tokens."""

from cryptography.fernet import Fernet, InvalidToken


class TokenCipher:
    def __init__(self, key: str):
        if not key:
            raise ValueError("WORKFLOW_ENCRYPTION_KEY is required for token encryption")
        self._fernet = Fernet(key.encode("utf-8"))

    @staticmethod
    def generate_key() -> str:
        return Fernet.generate_key().decode("utf-8")

    def encrypt(self, plaintext: str) -> str:
        if plaintext is None:
            raise ValueError("Cannot encrypt None")
        return self._fernet.encrypt(plaintext.encode("utf-8")).decode("utf-8")

    def decrypt(self, ciphertext: str) -> str:
        try:
            return self._fernet.decrypt(ciphertext.encode("utf-8")).decode("utf-8")
        except InvalidToken as exc:
            raise ValueError("Invalid encrypted token") from exc
