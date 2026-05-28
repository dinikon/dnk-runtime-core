from pydantic import BaseModel

from src.modules.segmentation.presentation.http.segment_snapshot.responses.segment_snapshot_response import (
    SegmentSnapshotResponseSchema,
)


class ListSegmentSnapshotsResponseSchema(BaseModel):
    """Segment snapshots list response schema."""

    items: list[SegmentSnapshotResponseSchema]
    count: int


__all__ = ["ListSegmentSnapshotsResponseSchema"]
