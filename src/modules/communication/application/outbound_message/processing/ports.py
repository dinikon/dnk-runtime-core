from __future__ import annotations

from datetime import datetime
from typing import Any, AsyncContextManager, Protocol

from src.modules.communication.domain.delivery import DeliveryAttempt
from src.modules.communication.domain.message_template import (
    MessageTemplateEntity,
    TemplateVersionEntity,
)
from src.modules.communication.domain.outbound_message import (
    CommunicationRequest,
    OutboundMessage,
    OutboundMessageIdVO,
)
from src.modules.communication.domain.provider_connection import (
    ProviderConnectionEntity,
    ProviderConnectionIdVO,
)
from src.modules.communication.domain.provider_connector import (
    ProviderConnector,
    ProviderMessageType,
)
from src.modules.shared import EntityIdVO

ProcessingContext = tuple[
    OutboundMessage,
    CommunicationRequest,
    MessageTemplateEntity,
    TemplateVersionEntity,
    ProviderConnectionEntity,
    ProviderConnector,
    ProviderMessageType,
]


class OutboundProcessingRepositoryProtocol(Protocol):
    """Порт runtime операций batch processing outbound messages."""

    async def claim_queued_messages(
        self,
        tenant_id: EntityIdVO,
        limit: int,
    ) -> list[OutboundMessage]:
        """Захватывает queued messages для обработки."""
        ...

    async def load_processing_context(
        self,
        tenant_id: EntityIdVO,
        outbound_message_id: OutboundMessageIdVO,
    ) -> ProcessingContext:
        """Загружает полный контекст обработки outbound message."""
        ...

    async def create_delivery_attempt(
        self,
        *,
        tenant_id: EntityIdVO,
        outbound_message_id: OutboundMessageIdVO,
        provider_connection_id: ProviderConnectionIdVO,
        request_payload: dict[str, Any],
    ) -> DeliveryAttempt:
        """Создает delivery attempt для provider request."""
        ...

    async def complete_outbound_processing(self, **kwargs: Any) -> bool:
        """Фиксирует успешную provider processing операцию."""
        ...

    async def fail_outbound_processing(self, **kwargs: Any) -> bool:
        """Фиксирует ошибку provider processing операции."""
        ...


class OutboundProcessingByIdRepositoryProtocol(
    OutboundProcessingRepositoryProtocol,
    Protocol,
):
    """Порт обработки одного outbound message с lease."""

    async def claim_outbound_for_processing(
        self,
        *,
        tenant_id: EntityIdVO,
        outbound_message_id: OutboundMessageIdVO,
        processing_token: EntityIdVO,
        now: datetime,
        lease_until: datetime,
    ) -> OutboundMessage | None:
        """Пытается захватить outbound message по id."""
        ...

    async def get_outbound_by_id(
        self,
        tenant_id: EntityIdVO,
        outbound_message_id: OutboundMessageIdVO,
    ) -> OutboundMessage | None:
        """Возвращает outbound message по id."""
        ...


class OutboundProcessingRepositoryContextFactoryProtocol(Protocol):
    """Фабрика transaction-scoped repository context для by-id processing."""

    def __call__(
        self,
    ) -> AsyncContextManager[OutboundProcessingByIdRepositoryProtocol]:
        """Возвращает async context manager с repository."""
        ...


__all__ = [
    "OutboundProcessingByIdRepositoryProtocol",
    "OutboundProcessingRepositoryContextFactoryProtocol",
    "OutboundProcessingRepositoryProtocol",
    "ProcessingContext",
]
