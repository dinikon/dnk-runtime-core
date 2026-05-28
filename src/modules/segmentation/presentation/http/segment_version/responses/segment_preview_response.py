from uuid import UUID

from pydantic import BaseModel


class SegmentPreviewContactResponseSchema(BaseModel):
    """Contact summary returned in segment preview response."""

    id: UUID
    first_name: str
    last_name: str | None
    middle_name: str | None
    status: str | None


class SegmentPreviewResponseSchema(BaseModel):
    """Segment preview response schema."""

    contact_ids: list[UUID]
    items: list[SegmentPreviewContactResponseSchema]
    limit: int
    offset: int
    count: int
    total: int | None = None
    has_more: bool


__all__ = [
    "SegmentPreviewContactResponseSchema",
    "SegmentPreviewResponseSchema",
]
