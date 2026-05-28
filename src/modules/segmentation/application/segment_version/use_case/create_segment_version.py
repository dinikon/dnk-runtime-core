from typing import Protocol

from src.modules.segmentation.application.segment_version.command import (
    CreateSegmentVersionCommand,
)
from src.modules.segmentation.application.segment_version.dto import (
    SegmentVersionDTO,
    build_segment_config_checksum,
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
    SegmentVersion,
    SegmentVersionCommandRepositoryProtocol,
    SegmentVersionError,
    SegmentVersionIdVO,
    SegmentVersionStatusVO,
)
from src.modules.shared import UuidPort


class CreateSegmentVersionUseCaseProtocol(Protocol):
    """Use case port for creating segment version."""

    async def __call__(
        self,
        command: CreateSegmentVersionCommand,
    ) -> SegmentVersionDTO:
        """Creates draft segment version."""
        ...


class CreateSegmentVersionUseCase:
    """Creates draft Contact segment version."""

    def __init__(
        self,
        *,
        segment_repository: SegmentDefinitionCommandRepositoryProtocol,
        version_command_repository: SegmentVersionCommandRepositoryProtocol,
        version_query_repository: SegmentVersionQueryRepositoryProtocol,
        uuid_generator: UuidPort,
    ) -> None:
        self._segment_repository = segment_repository
        self._version_command_repository = version_command_repository
        self._version_query_repository = version_query_repository
        self._uuid_generator = uuid_generator

    async def __call__(
        self,
        command: CreateSegmentVersionCommand,
    ) -> SegmentVersionDTO:
        segment = await self._segment_repository.load(
            tenant_id=command.tenant_id,
            segment_id=command.segment_id,
        )
        if segment is None:
            raise SegmentDefinitionNotFoundError(str(command.segment_id))
        if segment.status == SegmentStatusVO.ARCHIVED:
            raise SegmentDefinitionArchivedError(str(command.segment_id))

        version_number = await self._version_command_repository.get_next_version_number(
            tenant_id=command.tenant_id,
            segment_id=command.segment_id,
        )
        version = SegmentVersion(
            segment_version_id=SegmentVersionIdVO.from_value(
                self._uuid_generator.new_uuid()
            ),
            segment_id=command.segment_id,
            version_number=version_number,
            status=SegmentVersionStatusVO.DRAFT,
            config=dict(command.config),
            config_checksum=build_segment_config_checksum(command.config),
        )
        saved = await self._version_command_repository.save(
            tenant_id=command.tenant_id,
            version=version,
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
    "CreateSegmentVersionUseCase",
    "CreateSegmentVersionUseCaseProtocol",
]
