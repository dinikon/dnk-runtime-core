from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True, slots=True)
class MessageTemplateDTO:
    """DTO message template для application/presentation boundary."""

    template_id: UUID
    tenant_id: UUID
    name: str
    description: str | None
    provider_connector_id: UUID
    provider_message_type_id: UUID
    channel_code: str
    status: str
    created_at: datetime
    updated_at: datetime
    active_version_id: UUID | None = None
    active_version: datetime | None = None


__all__ = ["MessageTemplateDTO"]
