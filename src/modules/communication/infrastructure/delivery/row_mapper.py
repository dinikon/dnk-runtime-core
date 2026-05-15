from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import Any
from uuid import UUID

from src.modules.communication.domain.delivery import (
    DeliveryAttempt,
    DeliveryAttemptIdVO,
    DeliveryEvent,
    DeliveryEventIdVO,
)
from src.modules.communication.domain.outbound_message import OutboundMessageIdVO
from src.modules.communication.domain.provider_connection import (
    ProviderConnectionIdVO,
)
from src.modules.shared import EntityIdVO


def delivery_attempt_entity(row: Mapping[str, Any]) -> DeliveryAttempt:
    """Мапит runtime row в DeliveryAttempt."""
    return DeliveryAttempt(
        delivery_attempt_id=DeliveryAttemptIdVO.from_value(as_uuid(row.get("id"))),
        outbound_message_id=OutboundMessageIdVO.from_value(
            as_uuid(row.get("outbound_message_id"))
        ),
        provider_connection_id=ProviderConnectionIdVO.from_value(
            as_uuid(row.get("provider_connection_id"))
        ),
        attempt_no=int(row.get("attempt_no")),
        status=as_str(row.get("status")),
        request_payload=as_optional_dict(row.get("request_payload")),
        response_payload=as_optional_dict(row.get("response_payload")),
        http_status_code=(
            None
            if row.get("http_status_code") is None
            else int(row.get("http_status_code"))
        ),
        external_message_id=as_optional_str(row.get("external_message_id")),
        error_code=as_optional_str(row.get("error_code")),
        error_message=as_optional_str(row.get("error_message")),
        started_at=as_optional_datetime(row.get("started_at")),
        finished_at=as_optional_datetime(row.get("finished_at")),
    )


def delivery_event_entity(
    *,
    tenant_id: EntityIdVO,
    row: Mapping[str, Any],
) -> DeliveryEvent:
    """Мапит runtime row в DeliveryEvent."""
    outbound_message_id = as_optional_uuid(row.get("outbound_message_id"))
    provider_connection_id = as_optional_uuid(row.get("provider_connection_id"))
    return DeliveryEvent(
        delivery_event_id=DeliveryEventIdVO.from_value(as_uuid(row.get("id"))),
        tenant_id=tenant_id,
        outbound_message_id=(
            None
            if outbound_message_id is None
            else OutboundMessageIdVO.from_value(outbound_message_id)
        ),
        provider_connection_id=(
            None
            if provider_connection_id is None
            else ProviderConnectionIdVO.from_value(provider_connection_id)
        ),
        external_message_id=as_optional_str(row.get("external_message_id")),
        external_status=as_optional_str(row.get("external_status")),
        internal_status=as_str(row.get("internal_status")),
        event_type=as_str(row.get("event_type")),
        event_at=as_optional_datetime(row.get("event_at")),
        raw_payload=as_dict(row.get("raw_payload")),
        created_at=as_datetime(row.get("created_at")),
    )


def as_uuid(value: Any) -> UUID:
    """Достает UUID из runtime row."""
    if isinstance(value, UUID):
        return value
    if isinstance(value, str):
        return UUID(value)
    if isinstance(value, EntityIdVO):
        return value.uuid
    raise TypeError("Communication delivery runtime row must contain UUID value.")


def as_optional_uuid(value: Any) -> UUID | None:
    """Достает optional UUID из runtime row."""
    if value is None:
        return None
    return as_uuid(value)


def as_datetime(value: Any) -> datetime:
    """Достает datetime из runtime row."""
    if isinstance(value, datetime):
        return value
    raise TypeError("Communication delivery runtime row must contain datetime value.")


def as_optional_datetime(value: Any) -> datetime | None:
    """Достает optional datetime из runtime row."""
    if value is None:
        return None
    return as_datetime(value)


def as_str(value: Any) -> str:
    """Достает строку из runtime row."""
    if isinstance(value, str):
        return value
    raise TypeError("Communication delivery runtime row must contain string value.")


def as_optional_str(value: Any) -> str | None:
    """Достает optional строку из runtime row."""
    if value is None:
        return None
    return as_str(value)


def as_dict(value: Any) -> dict[str, Any]:
    """Достает dict из runtime row."""
    if value is None:
        return {}
    if isinstance(value, dict):
        return dict(value)
    raise TypeError("Communication delivery runtime row must contain dict value.")


def as_optional_dict(value: Any) -> dict[str, Any] | None:
    """Достает optional dict из runtime row."""
    if value is None:
        return None
    return as_dict(value)


__all__ = [
    "delivery_attempt_entity",
    "delivery_event_entity",
]
