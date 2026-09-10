from __future__ import annotations

from enum import StrEnum


class SystemEmailKind(StrEnum):
    """Виды системных email-писем, доступных бизнес-модулям."""

    SEND_OTP_CODE = "send_otp_code"


__all__ = ["SystemEmailKind"]
