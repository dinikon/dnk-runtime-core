from __future__ import annotations

from src.modules.identity.application.email.email_service_port import EmailServicePort
from src.modules.identity.application.email.system_email_kind import SystemEmailKind
from src.modules.shared.application.email.email_transport_port import EmailTransportPort
from src.modules.identity.infrastructure.email.render_system_email import (
    render_system_email,
)


class SystemEmailService(EmailServicePort):
    """Сервис писем Identity, принимающий типизированные виды системных писем."""

    def __init__(self, transport: EmailTransportPort) -> None:
        self._transport = transport

    async def send(
        self,
        kind: SystemEmailKind,
        recipient_email: str,
        variables: object,
    ) -> None:
        """Рендерит системное письмо и передает его в transport."""
        await self._transport.send(
            render_system_email(
                kind=kind,
                recipient_email=recipient_email,
                variables=variables,
            )
        )


__all__ = ["SystemEmailService"]
