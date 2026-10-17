from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ConfirmEmailOtpCommand:
    """DTO команды подтверждения email OTP."""

    host: str
    email: str
    token: str
    code: str
