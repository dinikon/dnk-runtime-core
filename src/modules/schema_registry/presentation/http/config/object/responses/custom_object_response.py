from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from src.modules.schema_registry.presentation.http.config.field.responses import (
    CustomFieldResponseSchema,
)


class CustomObjectResponseSchema(BaseModel):
    """HTTP response schema для custom object."""

    id: UUID
    created_at: datetime
    updated_at: datetime
    singular_name: str
    plural_name: str
    singular_label: str
    plural_label: str
    description: str
    kind: str
    fields: list[CustomFieldResponseSchema]


__all__ = ["CustomObjectResponseSchema"]
