from __future__ import annotations

from typing import Literal, Protocol, overload

from src.modules.shared.domain.email import (
    SendOtpCodeVariables,
    SystemEmailKind,
)


class EmailServicePort(Protocol):
    """Порт отправки системных email-писем по typed kind/payload."""

    @overload
    async def send(
        self,
        kind: Literal[SystemEmailKind.SEND_OTP_CODE],
        recipient_email: str,
        variables: SendOtpCodeVariables,
    ) -> None: ...

    async def send(
        self,
        kind: SystemEmailKind,
        recipient_email: str,
        variables: object,
    ) -> None:
        """Отправляет системное письмо пользователю."""
        ...


__all__ = ["EmailServicePort"]
