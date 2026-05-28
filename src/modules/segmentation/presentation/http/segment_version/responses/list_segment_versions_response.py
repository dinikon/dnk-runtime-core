from pydantic import BaseModel

from src.modules.segmentation.presentation.http.segment_version.responses.segment_version_response import (
    SegmentVersionResponseSchema,
)


class ListSegmentVersionsResponseSchema(BaseModel):
    """HTTP response for segment versions list."""

    items: list[SegmentVersionResponseSchema]
    count: int


__all__ = ["ListSegmentVersionsResponseSchema"]
