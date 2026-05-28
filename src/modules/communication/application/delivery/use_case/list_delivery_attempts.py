from typing import Protocol

from src.modules.communication.application.delivery.dto import DeliveryAttemptDTO
from src.modules.communication.application.delivery.query import (
    DeliveryQueryRepositoryProtocol,
    ListDeliveryAttemptsQuery,
)


class ListDeliveryAttemptsUseCaseProtocol(Protocol):
    """Порт use case списка delivery attempts."""

    async def __call__(
        self,
        query: ListDeliveryAttemptsQuery,
    ) -> list[DeliveryAttemptDTO]:
        """Возвращает страницу delivery attempts."""
        ...


class ListDeliveryAttemptsUseCase:
    """Use case списка delivery attempts."""

    def __init__(self, repository: DeliveryQueryRepositoryProtocol) -> None:
        """Инициализирует use case query repository."""
        self._repository = repository

    async def __call__(
        self,
        query: ListDeliveryAttemptsQuery,
    ) -> list[DeliveryAttemptDTO]:
        """Возвращает DTO delivery attempts tenant."""
        return await self._repository.list_delivery_attempts(
            tenant_id=query.tenant_id,
            limit=query.limit,
            offset=query.offset,
            outbound_message_id=query.outbound_message_id,
            status=query.status,
        )


__all__ = [
    "ListDeliveryAttemptsUseCase",
    "ListDeliveryAttemptsUseCaseProtocol",
]
