"""Segment definition HTTP request schemas."""

__all__: list[str] = []
from src.modules.segmentation.presentation.http.segment_definition.requests.create_segment_definition_request import (
    CreateSegmentDefinitionRequestSchema,
)
from src.modules.segmentation.presentation.http.segment_definition.requests.update_segment_definition_request import (
    UpdateSegmentDefinitionRequestSchema,
)
from src.modules.segmentation.presentation.http.segment_definition.requests.preview_segment_definition_request import (
    PreviewSegmentDefinitionRequestSchema,
)

__all__ = [
    "CreateSegmentDefinitionRequestSchema",
    "PreviewSegmentDefinitionRequestSchema",
    "UpdateSegmentDefinitionRequestSchema",
]
