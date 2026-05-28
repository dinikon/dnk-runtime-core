from typing import Protocol

from src.modules.communication.application.delivery.dto import (
    DeliveryAttemptDTO,
    DeliveryEventDTO,
)
from src.modules.communication.domain.outbound_message import OutboundMessageIdVO
from src.modules.shared import EntityIdVO


class DeliveryQueryRepositoryProtocol(Protocol):
    """Порт query-чтения delivery attempts/events."""

    async def list_delivery_attempts(
        self,
        *,
        tenant_id: EntityIdVO,
        limit: int,
        offset: int,
        outbound_message_id: OutboundMessageIdVO | None = None,
        status: str | None = None,
    ) -> list[DeliveryAttemptDTO]:
        """Возвращает страницу delivery attempts."""
        ...

    async def list_delivery_events(
        self,
        *,
        tenant_id: EntityIdVO,
        limit: int,
        offset: int,
        outbound_message_id: OutboundMessageIdVO | None = None,
        external_message_id: str | None = None,
        internal_status: str | None = None,
        event_type: str | None = None,
    ) -> list[DeliveryEventDTO]:
        """Возвращает страницу delivery events."""
        ...


__all__ = ["DeliveryQueryRepositoryProtocol"]
