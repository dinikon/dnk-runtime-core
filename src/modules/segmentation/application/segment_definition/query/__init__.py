from src.modules.segmentation.application.segment_definition.query.get_segment_definition_query import (
    GetSegmentDefinitionQuery,
)
from src.modules.segmentation.application.segment_definition.query.list_segment_definitions_query import (
    ListSegmentDefinitionsQuery,
)
from src.modules.segmentation.application.segment_definition.query.repository import (
    SegmentDefinitionQueryRepositoryProtocol,
)

__all__ = [
    "GetSegmentDefinitionQuery",
    "ListSegmentDefinitionsQuery",
    "SegmentDefinitionQueryRepositoryProtocol",
]
