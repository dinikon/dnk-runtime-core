from __future__ import annotations

from cryptography.fernet import Fernet, InvalidToken


class SourceUrlCipher:
    """Encrypts partner URLs because their path/query often contains credentials."""

    def __init__(self, key: str) -> None:
        self.key = key

    @property
    def cipher(self):
        """Проверяет ключ только при операции с секретом."""
        if not self.key:
            raise RuntimeError("PRICE_LISTS__SOURCE_ENCRYPTION_KEY must be configured.")
        return Fernet(self.key.encode("ascii"))

    def encrypt(self, value: str) -> str:
        return self.cipher.encrypt(value.encode("utf-8")).decode("ascii")

    def decrypt(self, value: str) -> str:
        try:
            return self.cipher.decrypt(value.encode("ascii")).decode("utf-8")
        except InvalidToken as exc:
            raise RuntimeError("Price list source URL cannot be decrypted.") from exc


__all__ = ["SourceUrlCipher"]
