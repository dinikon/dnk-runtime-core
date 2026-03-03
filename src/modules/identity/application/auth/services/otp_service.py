from __future__ import annotations

import hashlib
import secrets
import string
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol


@dataclass(frozen=True, slots=True)
class GeneratedOtp:
    token: str
    code: str
    code_hash: str
    created_at: datetime


class OtpServiceProtocol(Protocol):
    def generate(self) -> GeneratedOtp: ...
    def verify_code(self, *, code: str, code_hash: str) -> bool: ...


class OtpService:
    def __init__(self, code_length: int):
        self._code_length = code_length

    def generate(self) -> GeneratedOtp:
        code = "".join(secrets.choice(string.digits) for _ in range(self._code_length))
        token = f"otp_{secrets.token_urlsafe(24)}"
        return GeneratedOtp(
            token=token,
            code=code,
            code_hash=self._hash_code(code),
            created_at=datetime.now(UTC),
        )

    def verify_code(self, *, code: str, code_hash: str) -> bool:
        return secrets.compare_digest(self._hash_code(code), code_hash)

    @staticmethod
    def _hash_code(code: str) -> str:
        return hashlib.sha256(code.encode("utf-8")).hexdigest()
