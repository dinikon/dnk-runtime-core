from uuid import UUID

from pydantic import BaseModel


class CreateSegmentSnapshotRequestSchema(BaseModel):
    """Request schema for creating segment snapshot."""

    segment_version_id: UUID | None = None


__all__ = ["CreateSegmentSnapshotRequestSchema"]
