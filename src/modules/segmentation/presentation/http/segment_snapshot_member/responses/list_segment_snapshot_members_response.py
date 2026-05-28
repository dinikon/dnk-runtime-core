from pydantic import BaseModel

from src.modules.segmentation.presentation.http.segment_snapshot_member.responses.segment_snapshot_member_response import (
    SegmentSnapshotMemberResponseSchema,
)


class ListSegmentSnapshotMembersResponseSchema(BaseModel):
    """Segment snapshot members list response schema."""

    items: list[SegmentSnapshotMemberResponseSchema]
    count: int


__all__ = ["ListSegmentSnapshotMembersResponseSchema"]
