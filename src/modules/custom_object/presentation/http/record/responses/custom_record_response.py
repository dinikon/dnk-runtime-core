from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel


class CustomRecordResponseSchema(BaseModel):
    """HTTP response schema custom-object record."""

    object_id: UUID
    row_id: UUID
    values: dict[str, Any]


__all__ = ["CustomRecordResponseSchema"]
