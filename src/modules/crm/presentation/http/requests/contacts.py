from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class CreateContactRequestSchema(BaseModel):
    last_name: str
    first_name: str
    middle_name: str | None = None
    custom_fields: dict[str, Any | None] = Field(default_factory=dict)


class UpdateContactRequestSchema(BaseModel):
    last_name: str
    first_name: str
    middle_name: str | None = None
    custom_fields: dict[str, Any | None] = Field(default_factory=dict)


__all__ = [
    "CreateContactRequestSchema",
    "UpdateContactRequestSchema",
]
