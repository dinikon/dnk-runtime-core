from src.modules.segmentation.domain.segment_definition.entity import SegmentDefinition
from src.modules.segmentation.domain.segment_definition.error import (
    InvalidSegmentDefinitionNameError,
    SegmentDefinitionArchivedError,
    SegmentDefinitionError,
    SegmentDefinitionKindChangeError,
    SegmentDefinitionNotFoundError,
)
from src.modules.segmentation.domain.segment_definition.repository import (
    SegmentDefinitionCommandRepositoryProtocol,
)
from src.modules.segmentation.domain.segment_definition.value_object import (
    SegmentIdVO,
    SegmentKindVO,
    SegmentStatusVO,
)

__all__ = [
    "SegmentDefinition",
    "SegmentDefinitionArchivedError",
    "SegmentDefinitionCommandRepositoryProtocol",
    "SegmentDefinitionError",
    "SegmentDefinitionKindChangeError",
    "SegmentDefinitionNotFoundError",
    "SegmentIdVO",
    "SegmentKindVO",
    "SegmentStatusVO",
    "InvalidSegmentDefinitionNameError",
]
