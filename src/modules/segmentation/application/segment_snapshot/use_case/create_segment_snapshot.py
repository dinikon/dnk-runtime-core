from typing import Protocol
from uuid import UUID

from src.modules.segmentation.application.segment_snapshot.command import (
    CreateSegmentSnapshotCommand,
)
from src.modules.segmentation.application.segment_snapshot.dto import SegmentSnapshotDTO
from src.modules.segmentation.application.segment_snapshot.query import (
    SegmentSnapshotQueryRepositoryProtocol,
)
from src.modules.segmentation.application.segment_version.evaluation import (
    SegmentVersionEvaluationOptions,
    SegmentVersionEvaluationService,
)
from src.modules.segmentation.domain.segment_definition import (
    SegmentDefinitionArchivedError,
    SegmentDefinitionCommandRepositoryProtocol,
    SegmentDefinitionNotFoundError,
    SegmentKindVO,
    SegmentStatusVO,
)
from src.modules.segmentation.domain.segment_snapshot import (
    SegmentSnapshot,
    SegmentSnapshotCommandRepositoryProtocol,
    SegmentSnapshotError,
    SegmentSnapshotIdVO,
)
from src.modules.segmentation.domain.segment_snapshot_member import (
    SegmentSnapshotMemberCommandRepositoryProtocol,
)
from src.modules.segmentation.domain.segment_version import (
    SegmentVersion,
    SegmentVersionCommandRepositoryProtocol,
    SegmentVersionNotFoundError,
)
from src.modules.segmentation.application.segment_version import (
    SegmentVersionActiveVersionNotFoundError,
)
from src.modules.shared import ClockPort, DomainError, EntityIdVO, UuidPort


class CreateSegmentSnapshotUseCaseProtocol(Protocol):
    """Use case port for creating segment snapshot."""

    async def __call__(
        self,
        command: CreateSegmentSnapshotCommand,
    ) -> SegmentSnapshotDTO:
        """Creates Contact segment snapshot synchronously."""
        ...


class CreateSegmentSnapshotUseCase:
    """Creates immutable Contact audience snapshot."""

    def __init__(
        self,
        *,
        segment_repository: SegmentDefinitionCommandRepositoryProtocol,
        version_repository: SegmentVersionCommandRepositoryProtocol,
        snapshot_command_repository: SegmentSnapshotCommandRepositoryProtocol,
        snapshot_query_repository: SegmentSnapshotQueryRepositoryProtocol,
        member_command_repository: SegmentSnapshotMemberCommandRepositoryProtocol,
        evaluation_service: SegmentVersionEvaluationService,
        clock: ClockPort,
        uuid_generator: UuidPort,
    ) -> None:
        self._segment_repository = segment_repository
        self._version_repository = version_repository
        self._snapshot_command_repository = snapshot_command_repository
        self._snapshot_query_repository = snapshot_query_repository
        self._member_command_repository = member_command_repository
        self._evaluation_service = evaluation_service
        self._clock = clock
        self._uuid_generator = uuid_generator

    async def __call__(
        self,
        command: CreateSegmentSnapshotCommand,
    ) -> SegmentSnapshotDTO:
        segment = await self._segment_repository.load(
            tenant_id=command.tenant_id,
            segment_id=command.segment_id,
        )
        if segment is None:
            raise SegmentDefinitionNotFoundError(str(command.segment_id.uuid))
        if segment.status == SegmentStatusVO.ARCHIVED:
            raise SegmentDefinitionArchivedError(str(command.segment_id.uuid))

        version = await self._resolve_version(command)
        snapshot = SegmentSnapshot.create(
            segment_snapshot_id=SegmentSnapshotIdVO.from_value(
                self._uuid_generator.new_uuid()
            ),
            segment_id=command.segment_id,
            segment_version_id=version.segment_version_id,
        )
        snapshot = await self._snapshot_command_repository.save(
            tenant_id=command.tenant_id,
            snapshot=snapshot,
        )
        snapshot = await self._snapshot_command_repository.save(
            tenant_id=command.tenant_id,
            snapshot=snapshot.start(now=self._clock.now()),
        )

        try:
            if segment.segment_kind == SegmentKindVO.STATIC:
                evaluation = await self._evaluation_service.evaluate_static_segment(
                    tenant_id=command.tenant_id,
                    segment_id=command.segment_id,
                    options=SegmentVersionEvaluationOptions(),
                )
            else:
                evaluation = await self._evaluation_service.evaluate_version(
                    tenant_id=command.tenant_id,
                    segment_id=command.segment_id,
                    segment_version_id=version.segment_version_id,
                    options=SegmentVersionEvaluationOptions(),
                )
            contact_ids = _dedupe_contact_ids(evaluation.contact_ids)
            member_count = await self._member_command_repository.add_members(
                tenant_id=command.tenant_id,
                segment_snapshot_id=snapshot.segment_snapshot_id,
                contact_ids=contact_ids,
                start_position=0,
            )
        except DomainError as exc:
            await self._member_command_repository.delete_for_failed_snapshot(
                tenant_id=command.tenant_id,
                segment_snapshot_id=snapshot.segment_snapshot_id,
            )
            await self._snapshot_command_repository.save(
                tenant_id=command.tenant_id,
                snapshot=snapshot.fail(
                    now=self._clock.now(),
                    error_code=exc.__class__.__name__,
                    error_message=str(exc),
                ),
            )
            raise

        saved = await self._snapshot_command_repository.save(
            tenant_id=command.tenant_id,
            snapshot=snapshot.complete(
                now=self._clock.now(),
                member_count=member_count,
            ),
        )
        dto = await self._snapshot_query_repository.get(
            tenant_id=command.tenant_id,
            segment_snapshot_id=saved.segment_snapshot_id,
        )
        if dto is None:
            raise SegmentSnapshotError(
                "Segment snapshot was saved but could not be loaded."
            )
        return dto

    async def _resolve_version(
        self,
        command: CreateSegmentSnapshotCommand,
    ) -> SegmentVersion:
        if command.segment_version_id is None:
            version = await self._version_repository.get_active(
                tenant_id=command.tenant_id,
                segment_id=command.segment_id,
            )
            if version is None:
                raise SegmentVersionActiveVersionNotFoundError(
                    str(command.segment_id.uuid)
                )
            return version

        version = await self._version_repository.load(
            tenant_id=command.tenant_id,
            segment_version_id=command.segment_version_id,
        )
        if version is None or version.segment_id != command.segment_id:
            raise SegmentVersionNotFoundError(str(command.segment_version_id.uuid))
        return version


def _dedupe_contact_ids(contact_ids: tuple[UUID, ...]) -> tuple[EntityIdVO, ...]:
    seen: set[UUID] = set()
    result: list[EntityIdVO] = []
    for contact_id in contact_ids:
        if contact_id in seen:
            continue
        seen.add(contact_id)
        result.append(EntityIdVO.from_value(contact_id))
    return tuple(result)


__all__ = [
    "CreateSegmentSnapshotUseCase",
    "CreateSegmentSnapshotUseCaseProtocol",
]
