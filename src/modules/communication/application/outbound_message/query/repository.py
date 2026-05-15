from typing import Protocol

from src.modules.communication.application.outbound_message.dto import (
    OutboundMessageDTO,
)
from src.modules.communication.domain.outbound_message import OutboundMessageIdVO
from src.modules.shared import EntityIdVO


class OutboundMessageQueryRepositoryProtocol(Protocol):
    """Порт query-чтения outbound messages."""

    async def get_outbound(
        self,
        *,
        tenant_id: EntityIdVO,
        outbound_message_id: OutboundMessageIdVO,
    ) -> OutboundMessageDTO | None:
        """Возвращает outbound message DTO по id."""
        ...

    async def list_outbound(
        self,
        *,
        tenant_id: EntityIdVO,
        limit: int,
        offset: int,
    ) -> list[OutboundMessageDTO]:
        """Возвращает страницу outbound message DTO."""
        ...


__all__ = ["OutboundMessageQueryRepositoryProtocol"]
