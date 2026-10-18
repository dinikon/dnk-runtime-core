from __future__ import annotations

from typing import Protocol

from src.modules.shared.application.email.rendered_email_message import (
    RenderedEmailMessage,
)


class EmailTransportPort(Protocol):
    """Общий контракт доставки готового письма."""

    async def send(self, message: RenderedEmailMessage) -> None:
        """Отправляет уже rendered письмо во внешний transport."""
        ...


__all__ = ["EmailTransportPort"]
