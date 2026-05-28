from typing import Protocol

from src.modules.segmentation.application.segment_definition.dto import (
    SegmentDefinitionDTO,
)
from src.modules.segmentation.application.segment_definition.query import (
    ListSegmentDefinitionsQuery,
    SegmentDefinitionQueryRepositoryProtocol,
)


class ListSegmentDefinitionsUseCaseProtocol(Protocol):
    """Use case port for listing segment definitions."""

    async def __call__(
        self,
        query: ListSegmentDefinitionsQuery,
    ) -> list[SegmentDefinitionDTO]:
        """Returns segment definition page."""
        ...


class ListSegmentDefinitionsUseCase:
    """Returns Contact segment definitions."""

    def __init__(self, repository: SegmentDefinitionQueryRepositoryProtocol) -> None:
        self._repository = repository

    async def __call__(
        self,
        query: ListSegmentDefinitionsQuery,
    ) -> list[SegmentDefinitionDTO]:
        return await self._repository.list(
            tenant_id=query.tenant_id,
            limit=query.limit,
            offset=query.offset,
        )


__all__ = [
    "ListSegmentDefinitionsUseCase",
    "ListSegmentDefinitionsUseCaseProtocol",
]
