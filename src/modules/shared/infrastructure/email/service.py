from __future__ import annotations

from src.modules.shared.infrastructure.email.ports import EmailTransportPort
from src.modules.shared.infrastructure.email.renderers import render_system_email
from src.modules.shared.kernel.email import EmailServicePort
from src.modules.shared.kernel.email.models import SystemEmailKind


class SystemEmailService(EmailServicePort):
    """Shared email service, принимающий typed system email kinds."""

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
