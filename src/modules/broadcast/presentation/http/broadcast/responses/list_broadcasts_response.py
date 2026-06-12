from __future__ import annotations

from pydantic import BaseModel

from src.modules.broadcast.presentation.http.broadcast.responses.broadcast_response import (
    BroadcastResponseSchema,
)


class BroadcastListPaginationResponseSchema(BaseModel):
    """Pydantic-схема pagination ответа списка broadcasts."""

    limit: int
    offset: int
    total: int


class ListBroadcastsResponseSchema(BaseModel):
    """HTTP response schema списка broadcasts."""

    data: list[BroadcastResponseSchema]
    pagination: BroadcastListPaginationResponseSchema


__all__ = [
    "BroadcastListPaginationResponseSchema",
    "ListBroadcastsResponseSchema",
]
