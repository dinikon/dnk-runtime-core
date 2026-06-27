from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import Any
from uuid import UUID

from src.modules.communication.application.outbound_message.dto import (
    OutboundMessageDTO,
)
from src.modules.communication.domain.message_template import (
    MessageTemplateIdVO,
    TemplateVersionIdVO,
)
from src.modules.communication.domain.outbound_message import (
    CommunicationRequest,
    CommunicationRequestIdVO,
    OutboundMessage,
    OutboundMessageIdVO,
)
from src.modules.communication.domain.provider_connection import (
    ProviderConnectionIdVO,
)
from src.modules.shared import EntityIdVO


def communication_request_entity(
    *,
    tenant_id: EntityIdVO,
    row: Mapping[str, Any],
) -> CommunicationRequest:
    """Мапит runtime row в CommunicationRequest."""
    return CommunicationRequest(
        communication_request_id=CommunicationRequestIdVO.from_value(
            as_uuid(row.get("id"))
        ),
        tenant_id=tenant_id,
        initiator_type=as_str(row.get("initiator_type")),
        initiator_ref_id=as_str(row.get("initiator_ref_id")),
        correlation_id=as_entity_id(row.get("correlation_id")),
        idempotency_key=as_str(row.get("idempotency_key")),
        channel_code=as_str(row.get("channel_code")),
        template_id=MessageTemplateIdVO.from_value(as_uuid(row.get("template_id"))),
        template_version_id=TemplateVersionIdVO.from_value(
            as_uuid(row.get("template_version_id"))
        ),
        recipient_identifier_type=as_str(row.get("recipient_identifier_type")),
        recipient_address=as_str(row.get("recipient_address")),
        recipient_snapshot=as_dict(row.get("recipient_snapshot")),
        variables=as_dict(row.get("variables")),
        scheduled_at=as_optional_datetime(row.get("scheduled_at")),
        priority=int(row.get("priority")),
        status=as_str(row.get("status")),
        created_at=as_datetime(row.get("created_at")),
        updated_at=as_datetime(row.get("updated_at")),
    )


def outbound_message_entity(
    *,
    tenant_id: EntityIdVO,
    row: Mapping[str, Any],
) -> OutboundMessage:
    """Мапит runtime row в OutboundMessage."""
    return OutboundMessage(
        outbound_message_id=OutboundMessageIdVO.from_value(as_uuid(row.get("id"))),
        tenant_id=tenant_id,
        communication_request_id=CommunicationRequestIdVO.from_value(
            as_uuid(row.get("communication_request_id"))
        ),
        provider_connection_id=ProviderConnectionIdVO.from_value(
            as_uuid(row.get("provider_connection_id"))
        ),
        channel_code=as_str(row.get("channel_code")),
        priority=int(row.get("priority")),
        recipient_identifier_type=as_str(row.get("recipient_identifier_type")),
        recipient_address=as_str(row.get("recipient_address")),
        recipient_snapshot=as_dict(row.get("recipient_snapshot")),
        rendered_payload=as_dict(row.get("rendered_payload")),
        provider_request_payload=as_dict(row.get("provider_request_payload")),
        external_message_id=as_optional_str(row.get("external_message_id")),
        external_status=as_optional_str(row.get("external_status")),
        internal_status=as_str(row.get("internal_status")),
        error_code=as_optional_str(row.get("error_code")),
        error_message=as_optional_str(row.get("error_message")),
        queued_at=as_optional_datetime(row.get("queued_at")),
        sent_at=as_optional_datetime(row.get("sent_at")),
        delivered_at=as_optional_datetime(row.get("delivered_at")),
        failed_at=as_optional_datetime(row.get("failed_at")),
        processing_token=as_optional_entity_id(row.get("processing_token")),
        processing_started_at=as_optional_datetime(row.get("processing_started_at")),
        processing_deadline_at=as_optional_datetime(row.get("processing_deadline_at")),
        next_attempt_at=as_optional_datetime(row.get("next_attempt_at")),
        queue_published_at=as_optional_datetime(row.get("queue_published_at")),
        queue_publish_count=int(row.get("queue_publish_count") or 0),
        created_at=as_datetime(row.get("created_at")),
        updated_at=as_datetime(row.get("updated_at")),
    )


def outbound_message_dto(
    *,
    tenant_id: EntityIdVO,
    row: Mapping[str, Any],
) -> OutboundMessageDTO:
    """Мапит runtime row в OutboundMessageDTO."""
    return OutboundMessageDTO(
        outbound_message_id=as_uuid(row.get("id")),
        tenant_id=tenant_id.uuid,
        communication_request_id=as_uuid(row.get("communication_request_id")),
        provider_connection_id=as_uuid(row.get("provider_connection_id")),
        channel_code=as_str(row.get("channel_code")),
        recipient_identifier_type=as_str(row.get("recipient_identifier_type")),
        recipient_address=as_str(row.get("recipient_address")),
        recipient_snapshot=as_dict(row.get("recipient_snapshot")),
        rendered_payload=as_dict(row.get("rendered_payload")),
        provider_request_payload=as_dict(row.get("provider_request_payload")),
        external_message_id=as_optional_str(row.get("external_message_id")),
        external_status=as_optional_str(row.get("external_status")),
        internal_status=as_str(row.get("internal_status")),
        error_code=as_optional_str(row.get("error_code")),
        error_message=as_optional_str(row.get("error_message")),
        queued_at=as_optional_datetime(row.get("queued_at")),
        sent_at=as_optional_datetime(row.get("sent_at")),
        delivered_at=as_optional_datetime(row.get("delivered_at")),
        failed_at=as_optional_datetime(row.get("failed_at")),
        created_at=as_datetime(row.get("created_at")),
        updated_at=as_datetime(row.get("updated_at")),
    )


def as_uuid(value: Any) -> UUID:
    """Достает UUID из runtime row."""
    if isinstance(value, UUID):
        return value
    if isinstance(value, str):
        return UUID(value)
    if isinstance(value, EntityIdVO):
        return value.uuid
    raise TypeError("Communication runtime row must contain UUID value.")


def as_optional_uuid(value: Any) -> UUID | None:
    """Достает optional UUID из runtime row."""
    if value is None:
        return None
    return as_uuid(value)


def as_datetime(value: Any) -> datetime:
    """Достает datetime из runtime row."""
    if isinstance(value, datetime):
        return value
    raise TypeError("Communication runtime row must contain datetime value.")


def as_optional_datetime(value: Any) -> datetime | None:
    """Достает optional datetime из runtime row."""
    if value is None:
        return None
    return as_datetime(value)


def as_str(value: Any) -> str:
    """Достает строку из runtime row."""
    if isinstance(value, str):
        return value
    raise TypeError("Communication runtime row must contain string value.")


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
    raise TypeError("Communication runtime row must contain dict value.")


def as_optional_dict(value: Any) -> dict[str, Any] | None:
    """Достает optional dict из runtime row."""
    if value is None:
        return None
    return as_dict(value)


def as_optional_entity_id(value: Any) -> EntityIdVO | None:
    """Достает optional EntityIdVO из runtime row."""
    if value is None:
        return None
    return EntityIdVO.from_value(as_uuid(value))


def as_entity_id(value: Any) -> EntityIdVO:
    """Достает EntityIdVO из runtime row."""
    return EntityIdVO.from_value(as_uuid(value))


__all__ = [
    "as_uuid",
    "communication_request_entity",
    "outbound_message_dto",
    "outbound_message_entity",
]
