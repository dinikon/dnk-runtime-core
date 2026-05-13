from typing import Protocol

from src.modules.communication.application.outbound_message.dto import (
    OutboundMessageDTO,
)
from src.modules.communication.application.outbound_message.query import (
    GetOutboundMessageQuery,
    OutboundMessageQueryRepositoryProtocol,
)
from src.modules.communication.domain.outbound_message import (
    OutboundMessageNotFoundError,
)


class GetOutboundMessageUseCaseProtocol(Protocol):
    """Порт use case получения outbound message."""

    async def __call__(self, query: GetOutboundMessageQuery) -> OutboundMessageDTO:
        """Возвращает outbound message DTO."""
        ...


class GetOutboundMessageUseCase:
    """Use case получения одного outbound message."""

    def __init__(self, repository: OutboundMessageQueryRepositoryProtocol) -> None:
        """Инициализирует use case query repository."""
        self._repository = repository

    async def __call__(self, query: GetOutboundMessageQuery) -> OutboundMessageDTO:
        """Возвращает outbound message DTO или поднимает not-found ошибку."""
        outbound = await self._repository.get_outbound(
            tenant_id=query.tenant_id,
            outbound_message_id=query.outbound_message_id,
        )
        if outbound is None:
            raise OutboundMessageNotFoundError()
        return outbound


__all__ = ["GetOutboundMessageUseCase", "GetOutboundMessageUseCaseProtocol"]
