from __future__ import annotations

from datetime import datetime
from typing import Any

from src.modules.communication.domain.delivery.entity import (
    DeliveryAttempt,
    DeliveryEvent,
)
from src.modules.communication.domain.delivery.enum import DeliveryEventType
from src.modules.communication.domain.delivery.repository import (
    DeliveryRepositoryProtocol,
)
from src.modules.communication.domain.delivery.value_object import (
    DeliveryAttemptIdVO,
    DeliveryEventIdVO,
)
from src.modules.communication.domain.outbound_message import (
    OutboundMessage,
    OutboundMessageIdVO,
)
from src.modules.communication.domain.provider_connection import (
    ProviderConnectionIdVO,
)
from src.modules.shared import EntityIdVO
from src.modules.shared.kernel.time.ports import ClockPort


class DeliveryService:
    """Доменный сервис delivery events и provider attempts."""

    def __init__(
        self,
        *,
        repository: DeliveryRepositoryProtocol,
        clock: ClockPort,
    ) -> None:
        """Инициализирует сервис delivery repository и clock-портом."""
        self._repository = repository
        self._clock = clock

    async def record_webhook_event(
        self,
        *,
        tenant_id: EntityIdVO,
        delivery_event_id: DeliveryEventIdVO,
        outbound: OutboundMessage,
        external_message_id: str,
        external_status: str | None,
        internal_status: str,
        event_at: datetime | None,
        raw_payload: dict[str, Any],
    ) -> DeliveryEvent:
        """Создает delivery event и обновляет outbound status."""
        now = self._clock.now()
        event = DeliveryEvent.create_from_webhook(
            delivery_event_id=delivery_event_id,
            tenant_id=tenant_id,
            outbound_message_id=outbound.outbound_message_id,
            provider_connection_id=outbound.provider_connection_id,
            external_message_id=external_message_id,
            external_status=external_status,
            internal_status=internal_status,
            event_type=_event_type_for_status(internal_status),
            event_at=event_at,
            raw_payload=raw_payload,
            now=now,
        )
        saved = await self._repository.add_delivery_event(
            tenant_id=tenant_id,
            event=event,
        )
        await self._repository.update_outbound_status_from_event(
            tenant_id=tenant_id,
            outbound_message_id=outbound.outbound_message_id,
            external_status=external_status,
            internal_status=internal_status,
            now=now,
        )
        return saved

    async def start_attempt(
        self,
        *,
        tenant_id: EntityIdVO,
        delivery_attempt_id: DeliveryAttemptIdVO,
        outbound_message_id: OutboundMessageIdVO,
        provider_connection_id: ProviderConnectionIdVO,
        request_payload: dict[str, Any],
    ) -> DeliveryAttempt:
        """Создает started delivery attempt через repository."""
        attempt_no = await self._repository.next_attempt_no(
            tenant_id=tenant_id,
            outbound_message_id=outbound_message_id,
        )
        attempt = DeliveryAttempt.start(
            delivery_attempt_id=delivery_attempt_id,
            outbound_message_id=outbound_message_id,
            provider_connection_id=provider_connection_id,
            attempt_no=attempt_no,
            request_payload=request_payload,
            started_at=self._clock.now(),
        )
        return await self._repository.save_delivery_attempt(
            tenant_id=tenant_id,
            attempt=attempt,
        )

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
        """Фиксирует успешное завершение delivery attempt."""
        attempt = await self._repository.get_delivery_attempt(
            tenant_id=tenant_id,
            delivery_attempt_id=delivery_attempt_id,
        )
        if attempt is None:
            return None
        attempt.complete_success(
            response_payload=response_payload,
            http_status_code=http_status_code,
            external_message_id=external_message_id,
            finished_at=finished_at,
        )
        return await self._repository.save_delivery_attempt(
            tenant_id=tenant_id,
            attempt=attempt,
        )

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
        """Фиксирует ошибку delivery attempt."""
        attempt = await self._repository.get_delivery_attempt(
            tenant_id=tenant_id,
            delivery_attempt_id=delivery_attempt_id,
        )
        if attempt is None:
            return None
        attempt.fail(
            retryable=retryable,
            error_code=error_code,
            error_message=error_message,
            finished_at=finished_at,
            response_payload=response_payload,
            http_status_code=http_status_code,
            external_message_id=external_message_id,
        )
        return await self._repository.save_delivery_attempt(
            tenant_id=tenant_id,
            attempt=attempt,
        )


def _event_type_for_status(internal_status: str) -> str:
    if internal_status in {item.value for item in DeliveryEventType}:
        return internal_status
    return DeliveryEventType.WEBHOOK_RECEIVED.value


__all__ = ["DeliveryService"]
