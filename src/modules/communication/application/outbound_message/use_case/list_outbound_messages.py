from typing import Protocol

from src.modules.communication.application.outbound_message.dto import (
    OutboundMessageDTO,
)
from src.modules.communication.application.outbound_message.query import (
    ListOutboundMessagesQuery,
    OutboundMessageQueryRepositoryProtocol,
)


class ListOutboundMessagesUseCaseProtocol(Protocol):
    """Порт use case списка outbound messages."""

    async def __call__(
        self,
        query: ListOutboundMessagesQuery,
    ) -> list[OutboundMessageDTO]:
        """Возвращает страницу outbound messages."""
        ...


class ListOutboundMessagesUseCase:
    """Use case списка outbound messages."""

    def __init__(self, repository: OutboundMessageQueryRepositoryProtocol) -> None:
        """Инициализирует use case query repository."""
        self._repository = repository

    async def __call__(
        self,
        query: ListOutboundMessagesQuery,
    ) -> list[OutboundMessageDTO]:
        """Возвращает DTO outbound messages tenant."""
        return await self._repository.list_outbound(
            tenant_id=query.tenant_id,
            limit=query.limit,
            offset=query.offset,
        )


__all__ = ["ListOutboundMessagesUseCase", "ListOutboundMessagesUseCaseProtocol"]
