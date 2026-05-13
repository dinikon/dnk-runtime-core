from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel


class TemplateVersionResponseSchema(BaseModel):
    """Pydantic-схема HTTP-ответа template version."""

    template_version_id: UUID
    template_id: UUID
    version: datetime
    template_payload: dict[str, Any]
    variables_schema: dict[str, Any]
    status: str
    created_at: datetime
    activated_at: datetime | None


__all__ = ["TemplateVersionResponseSchema"]
