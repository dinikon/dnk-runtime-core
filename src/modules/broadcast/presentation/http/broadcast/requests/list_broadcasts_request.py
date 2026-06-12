from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class BroadcastListPaginationRequestSchema(BaseModel):
    """Pydantic-схема pagination envelope списка broadcasts."""

    limit: int = Field(default=50, ge=1, le=500)
    offset: int = Field(default=0, ge=0)


class ListBroadcastsRequestSchema(BaseModel):
    """Pydantic-схема публичного списка broadcasts."""

    filter: dict[str, Any] | None = None
    sort: list[dict[str, Any]] = Field(default_factory=list)
    pagination: BroadcastListPaginationRequestSchema = Field(
        default_factory=BroadcastListPaginationRequestSchema
    )


__all__ = [
    "BroadcastListPaginationRequestSchema",
    "ListBroadcastsRequestSchema",
]
