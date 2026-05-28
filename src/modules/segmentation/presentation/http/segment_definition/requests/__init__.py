"""Segment definition HTTP request schemas."""

__all__: list[str] = []
from src.modules.segmentation.presentation.http.segment_definition.requests.create_segment_definition_request import (
    CreateSegmentDefinitionRequestSchema,
)
from src.modules.segmentation.presentation.http.segment_definition.requests.update_segment_definition_request import (
    UpdateSegmentDefinitionRequestSchema,
)

__all__ = [
    "CreateSegmentDefinitionRequestSchema",
    "UpdateSegmentDefinitionRequestSchema",
]
