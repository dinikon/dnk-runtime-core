from typing import Protocol

from src.modules.segmentation.application.segment_definition.dto import (
    SegmentDefinitionDTO,
)
from src.modules.segmentation.application.segment_definition.query import (
    GetSegmentDefinitionQuery,
    SegmentDefinitionQueryRepositoryProtocol,
)
from src.modules.segmentation.domain.segment_definition import (
    SegmentDefinitionNotFoundError,
)


class GetSegmentDefinitionUseCaseProtocol(Protocol):
    """Use case port for getting segment definition."""

    async def __call__(
        self,
        query: GetSegmentDefinitionQuery,
    ) -> SegmentDefinitionDTO:
        """Returns segment definition."""
        ...


class GetSegmentDefinitionUseCase:
    """Returns Contact segment definition."""

    def __init__(self, repository: SegmentDefinitionQueryRepositoryProtocol) -> None:
        self._repository = repository

    async def __call__(
        self,
        query: GetSegmentDefinitionQuery,
    ) -> SegmentDefinitionDTO:
        dto = await self._repository.get(
            tenant_id=query.tenant_id,
            segment_id=query.segment_id,
        )
        if dto is None:
            raise SegmentDefinitionNotFoundError(str(query.segment_id))
        return dto


__all__ = [
    "GetSegmentDefinitionUseCase",
    "GetSegmentDefinitionUseCaseProtocol",
]
