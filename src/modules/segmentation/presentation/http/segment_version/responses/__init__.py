"""Segment version HTTP response schemas."""

__all__: list[str] = []
from src.modules.segmentation.presentation.http.segment_version.responses.list_segment_versions_response import (
    ListSegmentVersionsResponseSchema,
)
from src.modules.segmentation.presentation.http.segment_version.responses.segment_version_response import (
    SegmentVersionResponseSchema,
)
from src.modules.segmentation.presentation.http.segment_version.responses.segment_preview_response import (
    SegmentPreviewContactResponseSchema,
    SegmentPreviewResponseSchema,
)

__all__ = [
    "ListSegmentVersionsResponseSchema",
    "SegmentPreviewContactResponseSchema",
    "SegmentPreviewResponseSchema",
    "SegmentVersionResponseSchema",
]
