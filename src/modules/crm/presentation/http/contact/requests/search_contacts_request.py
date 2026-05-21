from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ContactSearchPaginationRequestSchema(BaseModel):
    """Pydantic-схема pagination envelope для поиска контактов."""

    limit: int = Field(default=50, ge=1, le=100)
    offset: int = Field(default=0, ge=0)


class ContactSearchRequestSchema(BaseModel):
    """Pydantic-схема публичного search payload контактов."""

    filter: dict[str, Any] | None = None
    sort: list[dict[str, Any]] = Field(default_factory=list)
    pagination: ContactSearchPaginationRequestSchema


__all__ = [
    "ContactSearchPaginationRequestSchema",
    "ContactSearchRequestSchema",
]
