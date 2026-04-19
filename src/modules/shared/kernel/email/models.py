from __future__ import annotations

from enum import StrEnum
from typing import TypedDict


class SystemEmailKind(StrEnum):
    """Виды системных email-писем, доступных бизнес-модулям."""

    SEND_OTP_CODE = "send_otp_code"


class SendOtpCodeVariables(TypedDict):
    """Переменные для системного письма с OTP-кодом."""

    otp_code: str


__all__ = ["SendOtpCodeVariables", "SystemEmailKind"]
