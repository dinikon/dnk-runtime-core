"""Segment definition HTTP response schemas."""

__all__: list[str] = []
from src.modules.segmentation.presentation.http.segment_definition.responses.list_segment_definitions_response import (
    ListSegmentDefinitionsResponseSchema,
)
from src.modules.segmentation.presentation.http.segment_definition.responses.segment_definition_response import (
    SegmentDefinitionResponseSchema,
)
from src.modules.segmentation.presentation.http.segment_definition.responses.segment_preview_response import (
    SegmentPreviewContactResponseSchema,
    SegmentPreviewResponseSchema,
)

__all__ = [
    "ListSegmentDefinitionsResponseSchema",
    "SegmentDefinitionResponseSchema",
    "SegmentPreviewContactResponseSchema",
    "SegmentPreviewResponseSchema",
]
