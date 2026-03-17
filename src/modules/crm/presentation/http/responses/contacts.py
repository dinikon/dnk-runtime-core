from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class ContactResponseSchema(BaseModel):
    id: UUID
    created_at: datetime
    updated_at: datetime
    last_name: str
    first_name: str
    middle_name: str | None
    custom_fields: dict[str, Any | None] = Field(default_factory=dict)


__all__ = ["ContactResponseSchema"]
