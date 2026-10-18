from __future__ import annotations

from typing import TypedDict


class SendOtpCodeVariables(TypedDict):
    """Переменные для системного письма с OTP-кодом."""

    otp_code: str


__all__ = ["SendOtpCodeVariables"]
