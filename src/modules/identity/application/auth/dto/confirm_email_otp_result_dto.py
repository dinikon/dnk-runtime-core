from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class ConfirmEmailOtpResultDTO:
    """DTO результата подтверждения OTP и создания session."""

    ok: bool
    user_id: UUID
    tenant_id: UUID
    session_token: str
    expires_in: int


__all__ = ["ConfirmEmailOtpResultDTO"]
