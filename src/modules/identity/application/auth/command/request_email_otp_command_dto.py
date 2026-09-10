from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RequestEmailOtpCommandDTO:
    """DTO команды запроса email OTP для входа."""

    host: str
    email: str


__all__ = ["RequestEmailOtpCommandDTO"]
