from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class MessageTemplateResponseSchema(BaseModel):
    """Pydantic-схема HTTP-ответа message template."""

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
    active_version: datetime | None = None


__all__ = ["MessageTemplateResponseSchema"]
