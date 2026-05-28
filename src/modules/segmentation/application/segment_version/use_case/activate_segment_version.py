from typing import Protocol

from src.modules.segmentation.application.segment_version.command import (
    ActivateSegmentVersionCommand,
)
from src.modules.segmentation.application.segment_version.dto import (
    SegmentVersionDTO,
)
from src.modules.segmentation.application.segment_version.query import (
    SegmentVersionQueryRepositoryProtocol,
)
from src.modules.segmentation.domain.segment_definition import (
    SegmentDefinitionArchivedError,
    SegmentDefinitionCommandRepositoryProtocol,
    SegmentDefinitionNotFoundError,
    SegmentStatusVO,
)
from src.modules.segmentation.domain.segment_version import (
    SegmentVersionCommandRepositoryProtocol,
    SegmentVersionError,
    SegmentVersionNotFoundError,
)
from src.modules.shared import ClockPort


class ActivateSegmentVersionUseCaseProtocol(Protocol):
    """Use case port for activating segment version."""

    async def __call__(
        self,
        command: ActivateSegmentVersionCommand,
    ) -> SegmentVersionDTO:
        """Activates segment version."""
        ...


class ActivateSegmentVersionUseCase:
    """Activates Contact segment version and archives previous active versions."""

    def __init__(
        self,
        *,
        segment_repository: SegmentDefinitionCommandRepositoryProtocol,
        version_command_repository: SegmentVersionCommandRepositoryProtocol,
        version_query_repository: SegmentVersionQueryRepositoryProtocol,
        clock: ClockPort,
    ) -> None:
        self._segment_repository = segment_repository
        self._version_command_repository = version_command_repository
        self._version_query_repository = version_query_repository
        self._clock = clock

    async def __call__(
        self,
        command: ActivateSegmentVersionCommand,
    ) -> SegmentVersionDTO:
        segment = await self._segment_repository.load(
            tenant_id=command.tenant_id,
            segment_id=command.segment_id,
        )
        if segment is None:
            raise SegmentDefinitionNotFoundError(str(command.segment_id))
        if segment.status == SegmentStatusVO.ARCHIVED:
            raise SegmentDefinitionArchivedError(str(command.segment_id))

        version = await self._version_command_repository.load(
            tenant_id=command.tenant_id,
            segment_version_id=command.segment_version_id,
        )
        if version is None or version.segment_id != command.segment_id:
            raise SegmentVersionNotFoundError(str(command.segment_version_id))

        now = self._clock.now()
        activated = version.activate(now=now)
        await self._version_command_repository.archive_active_versions(
            tenant_id=command.tenant_id,
            segment_id=command.segment_id,
            now=now,
        )
        saved = await self._version_command_repository.save(
            tenant_id=command.tenant_id,
            version=activated,
        )
        dto = await self._version_query_repository.get(
            tenant_id=command.tenant_id,
            segment_id=saved.segment_id,
            segment_version_id=saved.segment_version_id,
        )
        if dto is None:
            raise SegmentVersionError(
                "Segment version was saved but could not be loaded."
            )
        return dto


__all__ = [
    "ActivateSegmentVersionUseCase",
    "ActivateSegmentVersionUseCaseProtocol",
]
