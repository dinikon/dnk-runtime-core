from __future__ import annotations

from datetime import datetime
from typing import Protocol

from src.modules.shared.application.messaging.broker_message import BrokerMessage


class MessagePublisherPort(Protocol):
    """Low-level broker publishing port for infrastructure adapters."""

    async def publish(
        self,
        *,
        exchange: str,
        routing_key: str,
        message: BrokerMessage,
        mandatory: bool = True,
        persist: bool = True,
        timestamp: datetime | None = None,
        message_type: str | None = None,
    ) -> None:
        """Publishes one broker message to an exchange and routing key."""
        ...


__all__ = ["MessagePublisherPort"]
