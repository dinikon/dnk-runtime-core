from __future__ import annotations

from cryptography.fernet import Fernet, InvalidToken

from src.config import dnk_config


class SourceUrlCipher:
    """Encrypts partner URLs because their path/query often contains credentials."""

    def __init__(self, key: str | None = None) -> None:
        configured = key or dnk_config.PRICE_LISTS.source_encryption_key
        if not configured:
            raise RuntimeError(
                "PRICE_LISTS__SOURCE_ENCRYPTION_KEY or "
                "PRICE_LISTS__ENCRYPTION_KEY_PATH must be configured."
            )
        self._cipher = Fernet(configured.encode("ascii"))

    def encrypt(self, value: str) -> str:
        return self._cipher.encrypt(value.encode("utf-8")).decode("ascii")

    def decrypt(self, value: str) -> str:
        try:
            return self._cipher.decrypt(value.encode("ascii")).decode("utf-8")
        except InvalidToken as exc:
            raise RuntimeError("Price list source URL cannot be decrypted.") from exc


__all__ = ["SourceUrlCipher"]
