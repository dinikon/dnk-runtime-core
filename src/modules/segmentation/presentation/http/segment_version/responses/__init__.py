"""Segment version HTTP response schemas."""

__all__: list[str] = []
from src.modules.segmentation.presentation.http.segment_version.responses.list_segment_versions_response import (
    ListSegmentVersionsResponseSchema,
)
from src.modules.segmentation.presentation.http.segment_version.responses.segment_version_response import (
    SegmentVersionResponseSchema,
)

__all__ = [
    "ListSegmentVersionsResponseSchema",
    "SegmentVersionResponseSchema",
]
