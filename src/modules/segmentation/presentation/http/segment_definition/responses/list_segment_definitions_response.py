from pydantic import BaseModel

from src.modules.segmentation.presentation.http.segment_definition.responses.segment_definition_response import (
    SegmentDefinitionResponseSchema,
)


class ListSegmentDefinitionsResponseSchema(BaseModel):
    """HTTP response for segment definitions list."""

    items: list[SegmentDefinitionResponseSchema]
    count: int


__all__ = ["ListSegmentDefinitionsResponseSchema"]
