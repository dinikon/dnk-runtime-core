from typing import Protocol

from src.modules.segmentation.application.segment_definition.command import (
    CreateSegmentDefinitionCommand,
)
from src.modules.segmentation.application.segment_definition.dto import (
    SegmentDefinitionDTO,
)
from src.modules.segmentation.application.segment_definition.query import (
    SegmentDefinitionQueryRepositoryProtocol,
)
from src.modules.segmentation.domain.segment_definition import (
    SegmentDefinition,
    SegmentDefinitionCommandRepositoryProtocol,
    SegmentDefinitionError,
    SegmentIdVO,
    SegmentStatusVO,
)
from src.modules.shared import UUIdGeneratorProtocol


class CreateSegmentDefinitionUseCaseProtocol(Protocol):
    """Use case port for creating segment definition."""

    async def __call__(
        self,
        command: CreateSegmentDefinitionCommand,
    ) -> SegmentDefinitionDTO:
        """Creates segment definition."""
        ...


class CreateSegmentDefinitionUseCase:
    """Creates Contact segment definition."""

    def __init__(
        self,
        *,
        command_repository: SegmentDefinitionCommandRepositoryProtocol,
        query_repository: SegmentDefinitionQueryRepositoryProtocol,
        uuid_generator: UUIdGeneratorProtocol,
    ) -> None:
        self._command_repository = command_repository
        self._query_repository = query_repository
        self._uuid_generator = uuid_generator

    async def __call__(
        self,
        command: CreateSegmentDefinitionCommand,
    ) -> SegmentDefinitionDTO:
        segment = SegmentDefinition(
            segment_id=SegmentIdVO.from_value(self._uuid_generator.new()),
            name=command.name,
            segment_kind=command.segment_kind,
            status=SegmentStatusVO.DRAFT,
            description=command.description,
        )
        saved = await self._command_repository.save(
            tenant_id=command.tenant_id,
            segment=segment,
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
    "CreateSegmentDefinitionUseCase",
    "CreateSegmentDefinitionUseCaseProtocol",
]
