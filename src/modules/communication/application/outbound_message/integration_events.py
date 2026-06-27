from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

import uuid6

from src.modules.communication.domain.outbound_message import (
    OutboundMessage,
    OutboundMessageStatus,
)
from src.modules.shared.domain.events import IntegrationEvent

OUTBOUND_MESSAGE_AGGREGATE_TYPE = "communication.outbound_message"
OUTBOUND_MESSAGE_SENT_EVENT = "communication.outbound_message.sent.v1"
OUTBOUND_MESSAGE_FAILED_EVENT = "communication.outbound_message.failed.v1"
OUTBOUND_MESSAGE_DELIVERED_EVENT = "communication.outbound_message.delivered.v1"
DELIVERY_STATUS_CHANGED_EVENT = "communication.delivery_status.changed.v1"
INTEGRATION_EVENT_VERSION = 1

_FAILED_STATUSES = {
    OutboundMessageStatus.FAILED.value,
    OutboundMessageStatus.EXPIRED.value,
    OutboundMessageStatus.UNDELIVERED.value,
}


def build_outbound_result_events(
    *,
    outbound: OutboundMessage,
    internal_status: str,
    external_status: str | None,
    external_message_id: str | None,
    occurred_at: datetime,
) -> list[IntegrationEvent]:
    """Builds public events for provider processing terminal outcomes."""
    if internal_status == OutboundMessageStatus.SENT.value:
        event_type = OUTBOUND_MESSAGE_SENT_EVENT
    elif internal_status == OutboundMessageStatus.DELIVERED.value:
        event_type = OUTBOUND_MESSAGE_DELIVERED_EVENT
    elif internal_status in _FAILED_STATUSES:
        event_type = OUTBOUND_MESSAGE_FAILED_EVENT
    else:
        return []
    return [
        _event(
            event_type=event_type,
            outbound=outbound,
            internal_status=internal_status,
            external_status=external_status,
            external_message_id=external_message_id,
            occurred_at=occurred_at,
        )
    ]


def build_delivery_status_events(
    *,
    outbound: OutboundMessage,
    internal_status: str,
    external_status: str | None,
    external_message_id: str | None,
    occurred_at: datetime,
) -> list[IntegrationEvent]:
    """Builds public events for provider webhook status changes."""
    events = [
        _event(
            event_type=DELIVERY_STATUS_CHANGED_EVENT,
            outbound=outbound,
            internal_status=internal_status,
            external_status=external_status,
            external_message_id=external_message_id,
            occurred_at=occurred_at,
        )
    ]
    if internal_status == OutboundMessageStatus.DELIVERED.value:
        events.append(
            _event(
                event_type=OUTBOUND_MESSAGE_DELIVERED_EVENT,
                outbound=outbound,
                internal_status=internal_status,
                external_status=external_status,
                external_message_id=external_message_id,
                occurred_at=occurred_at,
            )
        )
    return events


def _event(
    *,
    event_type: str,
    outbound: OutboundMessage,
    internal_status: str,
    external_status: str | None,
    external_message_id: str | None,
    occurred_at: datetime,
) -> IntegrationEvent:
    outbound_id = _id_uuid(outbound.outbound_message_id)
    return IntegrationEvent(
        event_id=uuid6.uuid7(),
        tenant_id=_id_uuid(outbound.tenant_id),
        event_type=event_type,
        event_version=INTEGRATION_EVENT_VERSION,
        aggregate_type=OUTBOUND_MESSAGE_AGGREGATE_TYPE,
        aggregate_id=outbound_id,
        payload={
            "outbound_message_id": str(outbound_id),
            "communication_request_id": str(
                _id_uuid(outbound.communication_request_id)
            ),
            "provider_connection_id": str(_id_uuid(outbound.provider_connection_id)),
            "channel_code": outbound.channel_code,
            "internal_status": internal_status,
            "external_status": external_status,
            "external_message_id": external_message_id,
            "occurred_at": occurred_at.isoformat(),
        },
        occurred_at=occurred_at,
    )


def _id_uuid(value: Any) -> UUID:
    if isinstance(value, UUID):
        return value
    if hasattr(value, "uuid"):
        return value.uuid
    raise TypeError("Communication id value must expose UUID.")


__all__ = [
    "DELIVERY_STATUS_CHANGED_EVENT",
    "OUTBOUND_MESSAGE_AGGREGATE_TYPE",
    "OUTBOUND_MESSAGE_DELIVERED_EVENT",
    "OUTBOUND_MESSAGE_FAILED_EVENT",
    "OUTBOUND_MESSAGE_SENT_EVENT",
    "build_delivery_status_events",
    "build_outbound_result_events",
]
