from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RequestEmailOtpResultDTO:
    """DTO результата создания OTP challenge."""

    token: str
    expires_in: int
    code: str | None = None


__all__ = ["RequestEmailOtpResultDTO"]
