from __future__ import annotations

from pydantic import BaseModel

from src.modules.custom_object.presentation.http.record.responses.custom_record_response import (
    CustomRecordResponseSchema,
)


class ListCustomRecordsResponseSchema(BaseModel):
    """HTTP response schema списка custom-object records."""

    items: list[CustomRecordResponseSchema]
    limit: int
    offset: int
    count: int


__all__ = ["ListCustomRecordsResponseSchema"]
