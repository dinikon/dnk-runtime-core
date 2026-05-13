from pydantic import BaseModel

from src.modules.communication.presentation.http.template.responses.message_template_response import (
    MessageTemplateResponseSchema,
)


class ListMessageTemplatesResponseSchema(BaseModel):
    """Pydantic-схема HTTP-ответа списка message templates."""

    items: list[MessageTemplateResponseSchema]


__all__ = ["ListMessageTemplatesResponseSchema"]
