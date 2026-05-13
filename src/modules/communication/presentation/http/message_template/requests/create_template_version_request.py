from typing import Any

from pydantic import BaseModel, Field


class CreateTemplateVersionRequestSchema(BaseModel):
    """Pydantic-схема тела запроса создания версии шаблона."""

    template_payload: dict[str, Any]
    variables_schema: dict[str, Any] = Field(default_factory=dict)


__all__ = ["CreateTemplateVersionRequestSchema"]
