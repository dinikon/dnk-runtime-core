from __future__ import annotations

from typing import Protocol

from src.modules.shared.infrastructure.email.rendered_email_message import (
    RenderedEmailMessage,
)


class EmailTransportPort(Protocol):
    """Internal transport-port для отправки уже собранного письма."""

    async def send(self, message: RenderedEmailMessage) -> None:
        """Отправляет уже rendered письмо во внешний transport."""
        ...


__all__ = ["EmailTransportPort"]
