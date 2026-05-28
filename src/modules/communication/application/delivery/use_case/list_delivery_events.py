from typing import Protocol

from src.modules.communication.application.delivery.dto import DeliveryEventDTO
from src.modules.communication.application.delivery.query import (
    DeliveryQueryRepositoryProtocol,
    ListDeliveryEventsQuery,
)


class ListDeliveryEventsUseCaseProtocol(Protocol):
    """Порт use case списка delivery events."""

    async def __call__(
        self,
        query: ListDeliveryEventsQuery,
    ) -> list[DeliveryEventDTO]:
        """Возвращает страницу delivery events."""
        ...


class ListDeliveryEventsUseCase:
    """Use case списка delivery events."""

    def __init__(self, repository: DeliveryQueryRepositoryProtocol) -> None:
        """Инициализирует use case query repository."""
        self._repository = repository

    async def __call__(
        self,
        query: ListDeliveryEventsQuery,
    ) -> list[DeliveryEventDTO]:
        """Возвращает DTO delivery events tenant."""
        return await self._repository.list_delivery_events(
            tenant_id=query.tenant_id,
            limit=query.limit,
            offset=query.offset,
            outbound_message_id=query.outbound_message_id,
            external_message_id=query.external_message_id,
            internal_status=query.internal_status,
            event_type=query.event_type,
        )


__all__ = [
    "ListDeliveryEventsUseCase",
    "ListDeliveryEventsUseCaseProtocol",
]
