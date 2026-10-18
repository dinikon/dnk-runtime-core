from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RequestEmailOtpCommand:
    """DTO команды запроса email OTP для входа."""

    host: str
    email: str
