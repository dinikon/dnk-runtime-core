from typing import Protocol

from src.modules.segmentation.application.segment_definition.command import (
    UpdateSegmentDefinitionCommand,
)
from src.modules.segmentation.application.segment_definition.dto import (
    SegmentDefinitionDTO,
)
from src.modules.segmentation.application.segment_definition.query import (
    SegmentDefinitionQueryRepositoryProtocol,
)
from src.modules.segmentation.domain.segment_definition import (
    SegmentDefinitionCommandRepositoryProtocol,
    SegmentDefinitionError,
    SegmentDefinitionNotFoundError,
)


class UpdateSegmentDefinitionUseCaseProtocol(Protocol):
    """Use case port for updating segment definition."""

    async def __call__(
        self,
        command: UpdateSegmentDefinitionCommand,
    ) -> SegmentDefinitionDTO:
        """Updates segment definition."""
        ...


class UpdateSegmentDefinitionUseCase:
    """Updates Contact segment definition."""

    def __init__(
        self,
        *,
        command_repository: SegmentDefinitionCommandRepositoryProtocol,
        query_repository: SegmentDefinitionQueryRepositoryProtocol,
    ) -> None:
        self._command_repository = command_repository
        self._query_repository = query_repository

    async def __call__(
        self,
        command: UpdateSegmentDefinitionCommand,
    ) -> SegmentDefinitionDTO:
        segment = await self._command_repository.load(
            tenant_id=command.tenant_id,
            segment_id=command.segment_id,
        )
        if segment is None:
            raise SegmentDefinitionNotFoundError(str(command.segment_id))
        updated = segment.update(
            name=command.name,
            description=command.description,
            description_provided=command.description_provided,
        )
        saved = await self._command_repository.save(
            tenant_id=command.tenant_id,
            segment=updated,
        )
        dto = await self._query_repository.get(
            tenant_id=command.tenant_id,
            segment_id=saved.segment_id,
        )
        if dto is None:
            raise SegmentDefinitionError(
                "Segment definition was saved but could not be loaded."
            )
        return dto


__all__ = [
    "UpdateSegmentDefinitionUseCase",
    "UpdateSegmentDefinitionUseCaseProtocol",
]
