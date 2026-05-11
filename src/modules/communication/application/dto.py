from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID


@dataclass(frozen=True, slots=True)
class ProviderConnectorDTO:
    provider_connector_id: UUID
    provider_code: str
    provider_name: str
    version: str
    connector_type: str
    channels: list[str]
    config_schema: dict[str, Any]
    secrets_schema: dict[str, Any]
    status: str
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class ProviderMessageTypeDTO:
    provider_message_type_id: UUID
    provider_connector_id: UUID
    message_type_code: str
    channel_code: str
    name: str
    field_schema: dict[str, Any]
    ui_schema: dict[str, Any]
    is_active: bool


@dataclass(frozen=True, slots=True)
class ProviderConnectionDTO:
    provider_connection_id: UUID
    tenant_id: UUID
    provider_connector_id: UUID
    connection_code: str
    connection_name: str
    channel_code: str
    config: dict[str, Any]
    secret_ref: str | None
    has_secrets: bool
    status: str
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class TemplateVersionDTO:
    template_version_id: UUID
    template_id: UUID
    version_no: int
    template_payload: dict[str, Any]
    variables_schema: dict[str, Any]
    status: str
    created_at: datetime
    activated_at: datetime | None


@dataclass(frozen=True, slots=True)
class MessageTemplateDTO:
    template_id: UUID
    tenant_id: UUID
    template_code: str
    name: str
    description: str | None
    provider_connector_id: UUID
    provider_message_type_id: UUID
    channel_code: str
    message_class: str
    status: str
    created_at: datetime
    updated_at: datetime
    active_version_id: UUID | None = None
    active_version_no: int | None = None


@dataclass(frozen=True, slots=True)
class SendCommunicationResultDTO:
    communication_request_id: UUID
    outbound_message_id: UUID
    status: str
    internal_status: str
    idempotent: bool


@dataclass(frozen=True, slots=True)
class OutboundMessageDTO:
    outbound_message_id: UUID
    tenant_id: UUID
    communication_request_id: UUID
    provider_connection_id: UUID
    channel_code: str
    contact_id: UUID | None
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
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class ProcessQueuedResultDTO:
    processed: int
    succeeded: int
    failed: int


@dataclass(frozen=True, slots=True)
class WebhookResultDTO:
    accepted: bool
    matched: bool
    outbound_message_id: UUID | None
    internal_status: str | None


__all__ = [
    "MessageTemplateDTO",
    "OutboundMessageDTO",
    "ProcessQueuedResultDTO",
    "ProviderConnectionDTO",
    "ProviderConnectorDTO",
    "ProviderMessageTypeDTO",
    "SendCommunicationResultDTO",
    "TemplateVersionDTO",
    "WebhookResultDTO",
]
