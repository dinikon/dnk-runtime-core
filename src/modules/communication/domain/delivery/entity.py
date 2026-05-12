from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from src.modules.communication.domain.delivery.value_object import (
    DeliveryAttemptIdVO,
    DeliveryEventIdVO,
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


@dataclass(slots=True)
class DeliveryEvent:
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


__all__ = [
    "DeliveryAttempt",
    "DeliveryEvent",
]
