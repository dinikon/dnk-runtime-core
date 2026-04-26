from __future__ import annotations

from pydantic import BaseModel

from src.modules.custom_object.presentation.http.object.responses.custom_object_response import (
    CustomObjectResponseSchema,
)


class ListCustomObjectsResponseSchema(BaseModel):
    """HTTP response schema списка custom objects."""

    items: list[CustomObjectResponseSchema]
    count: int


__all__ = ["ListCustomObjectsResponseSchema"]
