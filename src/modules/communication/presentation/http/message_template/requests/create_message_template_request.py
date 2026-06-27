from uuid import UUID

from pydantic import BaseModel


class CreateMessageTemplateRequestSchema(BaseModel):
    """Pydantic-схема тела запроса создания message template."""

    name: str
    description: str | None = None
    provider_connector_id: UUID
    provider_message_type_id: UUID
    channel_code: str


__all__ = ["CreateMessageTemplateRequestSchema"]
