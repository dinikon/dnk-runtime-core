from __future__ import annotations

import hashlib
import secrets
import string
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol


@dataclass(frozen=True, slots=True)
class GeneratedOtp:
    """Сгенерированный OTP token/code и hash для хранения challenge."""

    token: str
    code: str
    code_hash: str
    created_at: datetime


class OtpServiceProtocol(Protocol):
    """Порт генерации и проверки OTP-кодов."""

    def generate(self) -> GeneratedOtp:
        """Генерирует новый OTP challenge payload."""
        ...

    def verify_code(self, *, code: str, code_hash: str) -> bool:
        """Проверяет code против сохраненного hash."""
        ...


class OtpService:
    """Сервис генерации numeric OTP-кодов и secure token."""

    def __init__(self, code_length: int):
        """Сохраняет длину OTP-кода."""
        self._code_length = code_length

    def generate(self) -> GeneratedOtp:
        """Генерирует OTP code, login token, hash и timestamp."""
        code = "".join(secrets.choice(string.digits) for _ in range(self._code_length))
        token = f"otp_{secrets.token_urlsafe(24)}"
        return GeneratedOtp(
            token=token,
            code=code,
            code_hash=self._hash_code(code),
            created_at=datetime.now(UTC),
        )

    def verify_code(self, *, code: str, code_hash: str) -> bool:
        """Сравнивает hash code в constant-time режиме."""
        return secrets.compare_digest(self._hash_code(code), code_hash)

    @staticmethod
    def _hash_code(code: str) -> str:
        """Хеширует OTP code через SHA-256."""
        return hashlib.sha256(code.encode("utf-8")).hexdigest()


__all__ = ["GeneratedOtp", "OtpService", "OtpServiceProtocol"]
