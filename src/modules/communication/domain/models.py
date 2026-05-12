from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from src.modules.communication.domain.value_object import (
    CommunicationRequestIdVO,
    DeliveryAttemptIdVO,
    DeliveryEventIdVO,
    MessageTemplateIdVO,
    OutboundMessageIdVO,
    ProviderConnectionIdVO,
    ProviderConnectorIdVO,
    ProviderMessageTypeIdVO,
    TemplateVersionIdVO,
)
from src.modules.shared import EntityIdVO


@dataclass(slots=True)
class ProviderConnector:
    provider_connector_id: ProviderConnectorIdVO
    provider_code: str
    provider_name: str
    version: str
    connector_type: str
    yaml_spec: dict[str, Any]
    yaml_checksum: str
    status: str
    created_at: datetime
    updated_at: datetime


@dataclass(slots=True)
class ProviderMessageType:
    provider_message_type_id: ProviderMessageTypeIdVO
    provider_connector_id: ProviderConnectorIdVO
    message_type_code: str
    channel_code: str
    name: str
    field_schema: dict[str, Any]
    ui_schema: dict[str, Any]
    is_active: bool


@dataclass(slots=True)
class ProviderConnection:
    provider_connection_id: ProviderConnectionIdVO
    tenant_id: EntityIdVO
    provider_connector_id: ProviderConnectorIdVO
    connection_code: str
    connection_name: str
    channel_code: str
    config: dict[str, Any]
    secret_ref: str | None
    secrets_b64: str | None
    status: str
    created_at: datetime
    updated_at: datetime


@dataclass(slots=True)
class MessageTemplate:
    template_id: MessageTemplateIdVO
    tenant_id: EntityIdVO
    template_code: str
    name: str
    description: str | None
    provider_connector_id: ProviderConnectorIdVO
    provider_message_type_id: ProviderMessageTypeIdVO
    channel_code: str
    message_class: str
    status: str
    created_at: datetime
    updated_at: datetime


@dataclass(slots=True)
class TemplateVersion:
    template_version_id: TemplateVersionIdVO
    template_id: MessageTemplateIdVO
    version_no: int
    template_payload: dict[str, Any]
    variables_schema: dict[str, Any]
    status: str
    created_at: datetime
    activated_at: datetime | None


@dataclass(slots=True)
class CommunicationRequest:
    communication_request_id: CommunicationRequestIdVO
    tenant_id: EntityIdVO
    initiator_type: str
    initiator_ref_id: str | None
    correlation_id: EntityIdVO | None
    idempotency_key: str | None
    message_class: str
    channel_code: str
    template_id: MessageTemplateIdVO
    template_version_id: TemplateVersionIdVO
    contact_id: EntityIdVO | None
    recipient_address: str
    recipient_snapshot: dict[str, Any]
    variables: dict[str, Any]
    scheduled_at: datetime | None
    priority: int
    status: str
    created_at: datetime
    updated_at: datetime


@dataclass(slots=True)
class OutboundMessage:
    outbound_message_id: OutboundMessageIdVO
    tenant_id: EntityIdVO
    communication_request_id: CommunicationRequestIdVO
    provider_connection_id: ProviderConnectionIdVO
    channel_code: str
    message_class: str
    priority: int
    contact_id: EntityIdVO | None
    recipient_address: str
    rendered_payload: dict[str, Any]
    provider_request_payload: dict[str, Any]
    external_message_id: str | None
    external_status: str | None
    internal_status: str
    error_code: str | None
    error_message: str | None
    queued_at: datetime | None
    sent_at: datetime | None
    delivered_at: datetime | None
    failed_at: datetime | None
    processing_token: EntityIdVO | None
    processing_started_at: datetime | None
    processing_deadline_at: datetime | None
    next_attempt_at: datetime | None
    queue_published_at: datetime | None
    queue_publish_count: int
    created_at: datetime
    updated_at: datetime


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
    "CommunicationRequest",
    "DeliveryAttempt",
    "DeliveryEvent",
    "MessageTemplate",
    "OutboundMessage",
    "ProviderConnection",
    "ProviderConnector",
    "ProviderMessageType",
    "TemplateVersion",
]
