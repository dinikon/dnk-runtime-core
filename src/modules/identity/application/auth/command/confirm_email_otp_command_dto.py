from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ConfirmEmailOtpCommandDTO:
    """DTO команды подтверждения email OTP."""

    host: str
    email: str
    token: str
    code: str


__all__ = ["ConfirmEmailOtpCommandDTO"]
