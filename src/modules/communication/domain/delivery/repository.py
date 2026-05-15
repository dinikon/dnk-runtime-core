from __future__ import annotations

from datetime import datetime
from typing import Any
from typing import Protocol

from src.modules.communication.domain.delivery.entity import (
    DeliveryAttempt,
    DeliveryEvent,
)
from src.modules.communication.domain.delivery.value_object import (
    DeliveryAttemptIdVO,
)
from src.modules.communication.domain.outbound_message import (
    OutboundMessage,
    OutboundMessageIdVO,
)
from src.modules.communication.domain.provider_connection import (
    ProviderConnectionIdVO,
)
from src.modules.communication.domain.provider_connector import (
    ProviderConnector,
    ProviderConnectorCodeVO,
)
from src.modules.shared import EntityIdVO


class DeliveryAttemptRepositoryProtocol(Protocol):
    """Порт persistence операций delivery attempts."""

    async def get_delivery_attempt(
        self,
        *,
        tenant_id: EntityIdVO,
        delivery_attempt_id: DeliveryAttemptIdVO,
    ) -> DeliveryAttempt | None:
        """Загружает delivery attempt по id."""
        ...

    async def next_attempt_no(
        self,
        *,
        tenant_id: EntityIdVO,
        outbound_message_id: OutboundMessageIdVO,
    ) -> int:
        """Возвращает следующий attempt_no для outbound message."""
        ...

    async def save_delivery_attempt(
        self,
        *,
        tenant_id: EntityIdVO,
        attempt: DeliveryAttempt,
    ) -> DeliveryAttempt:
        """Создает или обновляет delivery attempt."""
        ...


class DeliveryEventRepositoryProtocol(Protocol):
    """Порт persistence операций delivery events."""

    async def add_delivery_event(
        self,
        *,
        tenant_id: EntityIdVO,
        event: DeliveryEvent,
    ) -> DeliveryEvent:
        """Создает delivery event."""
        ...

    async def update_outbound_status_from_event(
        self,
        *,
        tenant_id: EntityIdVO,
        outbound_message_id: OutboundMessageIdVO,
        external_status: str | None,
        internal_status: str,
        now: datetime,
    ) -> None:
        """Обновляет outbound status по provider delivery event."""
        ...


class DeliveryWebhookLookupProtocol(Protocol):
    """Порт lookup операций для provider webhook processing."""

    async def get_active_connector_by_code(
        self,
        *,
        tenant_id: EntityIdVO,
        provider_code: ProviderConnectorCodeVO,
    ) -> ProviderConnector | None:
        """Возвращает активный provider connector по коду."""
        ...

    async def find_outbound_by_external_message_id(
        self,
        *,
        tenant_id: EntityIdVO,
        external_message_id: str,
    ) -> OutboundMessage | None:
        """Ищет outbound message по external provider id."""
        ...


class DeliveryRepositoryProtocol(
    DeliveryAttemptRepositoryProtocol,
    DeliveryEventRepositoryProtocol,
    DeliveryWebhookLookupProtocol,
    Protocol,
):
    """Единый порт delivery aggregate repository."""


class DeliveryAttemptServiceProtocol(Protocol):
    """Порт сервиса delivery attempts для processing adapter."""

    async def start_attempt(
        self,
        *,
        tenant_id: EntityIdVO,
        delivery_attempt_id: DeliveryAttemptIdVO,
        outbound_message_id: OutboundMessageIdVO,
        provider_connection_id: ProviderConnectionIdVO,
        request_payload: dict[str, Any],
    ) -> DeliveryAttempt:
        """Создает started delivery attempt."""
        ...

    async def complete_attempt(
        self,
        *,
        tenant_id: EntityIdVO,
        delivery_attempt_id: DeliveryAttemptIdVO,
        response_payload: dict[str, Any],
        http_status_code: int | None,
        external_message_id: str | None,
        finished_at: datetime,
    ) -> DeliveryAttempt | None:
        """Фиксирует successful delivery attempt."""
        ...

    async def fail_attempt(
        self,
        *,
        tenant_id: EntityIdVO,
        delivery_attempt_id: DeliveryAttemptIdVO,
        retryable: bool,
        error_code: str,
        error_message: str,
        finished_at: datetime,
        response_payload: dict[str, Any] | None = None,
        http_status_code: int | None = None,
        external_message_id: str | None = None,
    ) -> DeliveryAttempt | None:
        """Фиксирует failed delivery attempt."""
        ...


__all__ = [
    "DeliveryAttemptRepositoryProtocol",
    "DeliveryAttemptServiceProtocol",
    "DeliveryEventRepositoryProtocol",
    "DeliveryRepositoryProtocol",
    "DeliveryWebhookLookupProtocol",
]
