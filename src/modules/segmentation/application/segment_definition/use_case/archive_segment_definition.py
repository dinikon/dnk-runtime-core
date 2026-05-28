from typing import Protocol

from src.modules.segmentation.application.segment_definition.command import (
    ArchiveSegmentDefinitionCommand,
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
from src.modules.shared import ClockPort


class ArchiveSegmentDefinitionUseCaseProtocol(Protocol):
    """Use case port for archiving segment definition."""

    async def __call__(
        self,
        command: ArchiveSegmentDefinitionCommand,
    ) -> SegmentDefinitionDTO:
        """Archives segment definition."""
        ...


class ArchiveSegmentDefinitionUseCase:
    """Archives Contact segment definition."""

    def __init__(
        self,
        *,
        command_repository: SegmentDefinitionCommandRepositoryProtocol,
        query_repository: SegmentDefinitionQueryRepositoryProtocol,
        clock: ClockPort,
    ) -> None:
        self._command_repository = command_repository
        self._query_repository = query_repository
        self._clock = clock

    async def __call__(
        self,
        command: ArchiveSegmentDefinitionCommand,
    ) -> SegmentDefinitionDTO:
        segment = await self._command_repository.load(
            tenant_id=command.tenant_id,
            segment_id=command.segment_id,
        )
        if segment is None:
            raise SegmentDefinitionNotFoundError(str(command.segment_id))
        archived = segment.archive(now=self._clock.now())
        saved = await self._command_repository.save(
            tenant_id=command.tenant_id,
            segment=archived,
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
    "ArchiveSegmentDefinitionUseCase",
    "ArchiveSegmentDefinitionUseCaseProtocol",
]
