from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Self

from src.modules.communication.domain.delivery.enum import (
    AttemptStatus,
    DeliveryEventType,
)
from src.modules.communication.domain.delivery.value_object import (
    DeliveryAttemptIdVO,
    DeliveryEventIdVO,
    ExternalMessageId,
)
from src.modules.communication.domain.outbound_message.value_object import (
    OutboundMessageIdVO,
)
from src.modules.communication.domain.provider_connection.value_object import (
    ProviderConnectionIdVO,
)
from src.modules.shared import EntityIdVO


@dataclass(slots=True)
class DeliveryAttempt:
    """Доменная сущность provider delivery attempt."""

    delivery_attempt_id: DeliveryAttemptIdVO
    outbound_message_id: OutboundMessageIdVO
    provider_connection_id: ProviderConnectionIdVO
    attempt_no: int
    status: str
    request_payload: dict[str, Any] | None
    response_payload: dict[str, Any] | None
    http_status_code: int | None
    external_message_id: str | None
    error_code: str | None
    error_message: str | None
    started_at: datetime | None
    finished_at: datetime | None

    @classmethod
    def start(
        cls,
        *,
        delivery_attempt_id: DeliveryAttemptIdVO,
        outbound_message_id: OutboundMessageIdVO,
        provider_connection_id: ProviderConnectionIdVO,
        attempt_no: int,
        request_payload: dict[str, Any],
        started_at: datetime,
    ) -> Self:
        """Создает started delivery attempt для provider request."""
        return cls(
            delivery_attempt_id=delivery_attempt_id,
            outbound_message_id=outbound_message_id,
            provider_connection_id=provider_connection_id,
            attempt_no=int(attempt_no),
            status=AttemptStatus.STARTED.value,
            request_payload=dict(request_payload),
            response_payload=None,
            http_status_code=None,
            external_message_id=None,
            error_code=None,
            error_message=None,
            started_at=started_at,
            finished_at=None,
        )

    def complete_success(
        self,
        *,
        response_payload: dict[str, Any],
        http_status_code: int | None,
        external_message_id: str | None,
        finished_at: datetime,
    ) -> None:
        """Фиксирует успешный ответ provider."""
        self.status = AttemptStatus.SUCCESS.value
        self.response_payload = dict(response_payload)
        self.http_status_code = http_status_code
        self.external_message_id = (
            None
            if external_message_id is None
            else ExternalMessageId(external_message_id).value
        )
        self.error_code = None
        self.error_message = None
        self.finished_at = finished_at

    def fail(
        self,
        *,
        retryable: bool,
        error_code: str,
        error_message: str,
        finished_at: datetime,
        response_payload: dict[str, Any] | None = None,
        http_status_code: int | None = None,
        external_message_id: str | None = None,
    ) -> None:
        """Фиксирует ошибку provider delivery attempt."""
        self.status = (
            AttemptStatus.RETRYABLE_FAILED.value
            if retryable
            else AttemptStatus.NON_RETRYABLE_FAILED.value
        )
        self.response_payload = (
            dict(response_payload)
            if response_payload is not None
            else {"error": error_message}
        )
        self.http_status_code = http_status_code
        self.external_message_id = (
            None
            if external_message_id is None
            else ExternalMessageId(external_message_id).value
        )
        self.error_code = str(error_code)
        self.error_message = str(error_message)
        self.finished_at = finished_at


@dataclass(slots=True)
class DeliveryEvent:
    """Доменная сущность provider delivery event."""

    delivery_event_id: DeliveryEventIdVO
    tenant_id: EntityIdVO
    outbound_message_id: OutboundMessageIdVO | None
    provider_connection_id: ProviderConnectionIdVO | None
    external_message_id: str | None
    external_status: str | None
    internal_status: str
    event_type: str
    event_at: datetime | None
    raw_payload: dict[str, Any]
    created_at: datetime

    @classmethod
    def create_from_webhook(
        cls,
        *,
        delivery_event_id: DeliveryEventIdVO,
        tenant_id: EntityIdVO,
        outbound_message_id: OutboundMessageIdVO,
        provider_connection_id: ProviderConnectionIdVO,
        external_message_id: str,
        external_status: str | None,
        internal_status: str,
        event_type: str,
        event_at: datetime | None,
        raw_payload: dict[str, Any],
        now: datetime,
    ) -> Self:
        """Создает delivery event из provider webhook payload."""
        try:
            event_type_value = DeliveryEventType(event_type).value
        except ValueError:
            event_type_value = DeliveryEventType.WEBHOOK_RECEIVED.value
        return cls(
            delivery_event_id=delivery_event_id,
            tenant_id=tenant_id,
            outbound_message_id=outbound_message_id,
            provider_connection_id=provider_connection_id,
            external_message_id=ExternalMessageId(external_message_id).value,
            external_status=(
                None if external_status is None else str(external_status).strip()
            ),
            internal_status=str(internal_status),
            event_type=event_type_value,
            event_at=event_at,
            raw_payload=dict(raw_payload),
            created_at=now,
        )


__all__ = [
    "DeliveryAttempt",
    "DeliveryEvent",
]
