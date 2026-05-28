from __future__ import annotations

import unittest
from datetime import UTC, datetime
from uuid import UUID, uuid4

from src.modules.segmentation.application.segment_snapshot import (
    CreateSegmentSnapshotCommand,
    CreateSegmentSnapshotUseCase,
    GetSegmentSnapshotQuery,
    GetSegmentSnapshotUseCase,
    ListSegmentSnapshotsQuery,
    ListSegmentSnapshotsUseCase,
    SegmentSnapshotDTO,
)
from src.modules.segmentation.application.segment_snapshot_member import (
    ListSegmentSnapshotMembersQuery,
    ListSegmentSnapshotMembersUseCase,
    SegmentSnapshotMemberDTO,
)
from src.modules.segmentation.application.segment_static_member.dto import (
    ContactSummaryDTO,
)
from src.modules.segmentation.application.segment_version import (
    SegmentVersionActiveVersionNotFoundError,
    SegmentVersionEvaluationError,
    SegmentVersionEvaluationResult,
)
from src.modules.segmentation.domain.segment_definition import (
    SegmentDefinition,
    SegmentDefinitionArchivedError,
    SegmentIdVO,
    SegmentKindVO,
    SegmentStatusVO,
)
from src.modules.segmentation.domain.segment_snapshot import (
    InvalidSegmentSnapshotError,
    SegmentSnapshot,
    SegmentSnapshotIdVO,
    SegmentSnapshotImmutableError,
    SegmentSnapshotNotFoundError,
    SegmentSnapshotStatusVO,
)
from src.modules.segmentation.domain.segment_snapshot_member import (
    InvalidSegmentSnapshotMemberError,
    SegmentSnapshotMember,
    SegmentSnapshotMemberIdVO,
)
from src.modules.segmentation.domain.segment_version import (
    SegmentVersion,
    SegmentVersionIdVO,
    SegmentVersionStatusVO,
)
from src.modules.shared import EntityIdVO


def _segment(
    segment_id: SegmentIdVO,
    *,
    kind: SegmentKindVO = SegmentKindVO.DYNAMIC,
    status: SegmentStatusVO = SegmentStatusVO.ACTIVE,
) -> SegmentDefinition:
    return SegmentDefinition(
        segment_id=segment_id,
        name="VIP",
        segment_kind=kind,
        status=status,
    )


def _version(
    segment_id: SegmentIdVO,
    version_id: SegmentVersionIdVO | None = None,
) -> SegmentVersion:
    return SegmentVersion(
        segment_version_id=version_id or SegmentVersionIdVO.from_value(uuid4()),
        segment_id=segment_id,
        version_number=1,
        status=SegmentVersionStatusVO.ACTIVE,
        config={"root_object": "contact"},
        config_checksum="abc",
    )


def _snapshot_dto(snapshot: SegmentSnapshot) -> SegmentSnapshotDTO:
    now = datetime(2026, 5, 28, 12, 0, tzinfo=UTC)
    return SegmentSnapshotDTO(
        id=snapshot.segment_snapshot_id.uuid,
        segment_id=snapshot.segment_id.uuid,
        segment_version_id=snapshot.segment_version_id.uuid,
        status=snapshot.status.value,
        member_count=snapshot.member_count,
        started_at=snapshot.started_at,
        completed_at=snapshot.completed_at,
        error_code=snapshot.error_code,
        error_message=snapshot.error_message,
        created_at=now,
        updated_at=now,
    )


class _ClockStub:
    def __init__(self) -> None:
        self.calls = 0

    def now(self) -> datetime:
        self.calls += 1
        return datetime(2026, 5, 28, 12, self.calls, tzinfo=UTC)


class _UuidStub:
    def __init__(self, value: UUID) -> None:
        self.value = value

    def new_uuid(self) -> UUID:
        return self.value


class _SegmentRepositoryStub:
    def __init__(self, segment: SegmentDefinition | None) -> None:
        self.segment = segment

    async def load(self, **kwargs):
        return self.segment


class _VersionRepositoryStub:
    def __init__(self, version: SegmentVersion | None) -> None:
        self.version = version
        self.active_calls = []
        self.load_calls = []

    async def load(self, **kwargs):
        self.load_calls.append(kwargs)
        return self.version

    async def get_active(self, **kwargs):
        self.active_calls.append(kwargs)
        return self.version


class _SnapshotCommandRepositoryStub:
    def __init__(
        self,
        query_repository: "_SnapshotQueryRepositoryStub | None" = None,
    ) -> None:
        self.saved: list[SegmentSnapshot] = []
        self.query_repository = query_repository

    async def load(self, **kwargs):
        return None

    async def save(self, **kwargs):
        snapshot = kwargs["snapshot"]
        self.saved.append(snapshot)
        if self.query_repository is not None:
            self.query_repository.snapshot = snapshot
        return snapshot


class _SnapshotQueryRepositoryStub:
    def __init__(self) -> None:
        self.snapshot: SegmentSnapshot | None = None
        self.items: list[SegmentSnapshotDTO] = []

    async def get(self, **kwargs):
        if self.snapshot is not None:
            return _snapshot_dto(self.snapshot)
        return None

    async def list(self, **kwargs):
        return self.items


class _MemberCommandRepositoryStub:
    def __init__(self) -> None:
        self.contact_ids: tuple[EntityIdVO, ...] = ()
        self.deleted_snapshot_ids: list[SegmentSnapshotIdVO] = []

    async def add_members(self, **kwargs):
        self.contact_ids = tuple(kwargs["contact_ids"])
        return len(self.contact_ids)

    async def delete_for_failed_snapshot(self, **kwargs):
        self.deleted_snapshot_ids.append(kwargs["segment_snapshot_id"])


class _EvaluationServiceStub:
    def __init__(
        self,
        contact_ids: tuple[UUID, ...] = (),
        exc: Exception | None = None,
    ) -> None:
        self.contact_ids = contact_ids
        self.exc = exc
        self.version_calls = []
        self.static_calls = []

    async def evaluate_version(self, **kwargs):
        self.version_calls.append(kwargs)
        if self.exc is not None:
            raise self.exc
        return SegmentVersionEvaluationResult(
            contact_ids=self.contact_ids,
            count=len(self.contact_ids),
        )

    async def evaluate_static_segment(self, **kwargs):
        self.static_calls.append(kwargs)
        if self.exc is not None:
            raise self.exc
        return SegmentVersionEvaluationResult(
            contact_ids=self.contact_ids,
            count=len(self.contact_ids),
        )


class _MemberQueryRepositoryStub:
    def __init__(self, items: list[SegmentSnapshotMemberDTO]) -> None:
        self.items = items

    async def list(self, **kwargs):
        return self.items


class _ContactLookupStub:
    def __init__(self, summaries=None) -> None:
        self.summaries = summaries or {}
        self.calls = []

    async def get_summaries(self, **kwargs):
        self.calls.append(kwargs)
        return self.summaries


class SegmentationSnapshotUseCaseTests(unittest.IsolatedAsyncioTestCase):
    def test_snapshot_domain_transitions_and_member_validation(self) -> None:
        now = datetime(2026, 5, 28, 12, 0, tzinfo=UTC)
        snapshot = SegmentSnapshot.create(
            segment_snapshot_id=SegmentSnapshotIdVO.from_value(uuid4()),
            segment_id=SegmentIdVO.from_value(uuid4()),
            segment_version_id=SegmentVersionIdVO.from_value(uuid4()),
        )

        running = snapshot.start(now=now)
        completed = running.complete(now=now, member_count=2)
        failed = snapshot.fail(
            now=now,
            error_code=" EVAL ",
            error_message=" bad config ",
        )

        self.assertEqual(running.status, SegmentSnapshotStatusVO.RUNNING)
        self.assertEqual(completed.status, SegmentSnapshotStatusVO.COMPLETED)
        self.assertEqual(completed.member_count, 2)
        self.assertEqual(failed.error_code, "EVAL")
        with self.assertRaises(SegmentSnapshotImmutableError):
            completed.fail(now=now, error_code="x", error_message="y")
        with self.assertRaises(InvalidSegmentSnapshotError):
            SegmentSnapshot.create(
                segment_snapshot_id=SegmentSnapshotIdVO.from_value(uuid4()),
                segment_id=SegmentIdVO.from_value(uuid4()),
                segment_version_id=SegmentVersionIdVO.from_value(uuid4()),
                member_count=-1,
            )
        with self.assertRaises(InvalidSegmentSnapshotMemberError):
            SegmentSnapshotMember.create(
                segment_snapshot_member_id=SegmentSnapshotMemberIdVO.from_value(
                    uuid4()
                ),
                segment_snapshot_id=SegmentSnapshotIdVO.from_value(uuid4()),
                contact_id=EntityIdVO.from_value(uuid4()),
                position=-1,
            )

    async def test_create_dynamic_snapshot_uses_active_version_and_dedupes_members(
        self,
    ) -> None:
        tenant_id = EntityIdVO.from_value(uuid4())
        segment_id = SegmentIdVO.from_value(uuid4())
        snapshot_id = uuid4()
        contact_a = uuid4()
        contact_b = uuid4()
        version = _version(segment_id)
        snapshot_query = _SnapshotQueryRepositoryStub()
        snapshot_command = _SnapshotCommandRepositoryStub(snapshot_query)
        member_command = _MemberCommandRepositoryStub()
        evaluation = _EvaluationServiceStub((contact_a, contact_b, contact_a))
        use_case = CreateSegmentSnapshotUseCase(
            segment_repository=_SegmentRepositoryStub(_segment(segment_id)),
            version_repository=_VersionRepositoryStub(version),
            snapshot_command_repository=snapshot_command,
            snapshot_query_repository=snapshot_query,
            member_command_repository=member_command,
            evaluation_service=evaluation,
            clock=_ClockStub(),
            uuid_generator=_UuidStub(snapshot_id),
        )

        result = await use_case(
            CreateSegmentSnapshotCommand(
                tenant_id=tenant_id,
                segment_id=segment_id,
            )
        )

        self.assertEqual(result.id, snapshot_id)
        self.assertEqual(result.segment_version_id, version.segment_version_id.uuid)
        self.assertEqual(result.status, "completed")
        self.assertEqual(result.member_count, 2)
        self.assertEqual(
            [snapshot.status for snapshot in snapshot_command.saved],
            [
                SegmentSnapshotStatusVO.PENDING,
                SegmentSnapshotStatusVO.RUNNING,
                SegmentSnapshotStatusVO.COMPLETED,
            ],
        )
        self.assertEqual(
            [item.uuid for item in member_command.contact_ids],
            [contact_a, contact_b],
        )
        self.assertEqual(
            evaluation.version_calls[0]["segment_version_id"],
            version.segment_version_id,
        )

    async def test_create_explicit_static_snapshot_stores_version_and_static_members(
        self,
    ) -> None:
        tenant_id = EntityIdVO.from_value(uuid4())
        segment_id = SegmentIdVO.from_value(uuid4())
        version_id = SegmentVersionIdVO.from_value(uuid4())
        version = _version(segment_id, version_id)
        evaluation = _EvaluationServiceStub((uuid4(),))
        snapshot_query = _SnapshotQueryRepositoryStub()
        use_case = CreateSegmentSnapshotUseCase(
            segment_repository=_SegmentRepositoryStub(
                _segment(segment_id, kind=SegmentKindVO.STATIC)
            ),
            version_repository=_VersionRepositoryStub(version),
            snapshot_command_repository=_SnapshotCommandRepositoryStub(snapshot_query),
            snapshot_query_repository=snapshot_query,
            member_command_repository=_MemberCommandRepositoryStub(),
            evaluation_service=evaluation,
            clock=_ClockStub(),
            uuid_generator=_UuidStub(uuid4()),
        )

        result = await use_case(
            CreateSegmentSnapshotCommand(
                tenant_id=tenant_id,
                segment_id=segment_id,
                segment_version_id=version_id,
            )
        )

        self.assertEqual(result.segment_version_id, version_id.uuid)
        self.assertEqual(len(evaluation.static_calls), 1)
        self.assertEqual(evaluation.version_calls, [])

    async def test_create_snapshot_rejects_archived_and_missing_active_segment(
        self,
    ) -> None:
        tenant_id = EntityIdVO.from_value(uuid4())
        segment_id = SegmentIdVO.from_value(uuid4())

        archived_use_case = CreateSegmentSnapshotUseCase(
            segment_repository=_SegmentRepositoryStub(
                _segment(segment_id, status=SegmentStatusVO.ARCHIVED)
            ),
            version_repository=_VersionRepositoryStub(_version(segment_id)),
            snapshot_command_repository=_SnapshotCommandRepositoryStub(),
            snapshot_query_repository=_SnapshotQueryRepositoryStub(),
            member_command_repository=_MemberCommandRepositoryStub(),
            evaluation_service=_EvaluationServiceStub(),
            clock=_ClockStub(),
            uuid_generator=_UuidStub(uuid4()),
        )
        with self.assertRaises(SegmentDefinitionArchivedError):
            await archived_use_case(
                CreateSegmentSnapshotCommand(
                    tenant_id=tenant_id,
                    segment_id=segment_id,
                )
            )

        missing_active_use_case = CreateSegmentSnapshotUseCase(
            segment_repository=_SegmentRepositoryStub(_segment(segment_id)),
            version_repository=_VersionRepositoryStub(None),
            snapshot_command_repository=_SnapshotCommandRepositoryStub(),
            snapshot_query_repository=_SnapshotQueryRepositoryStub(),
            member_command_repository=_MemberCommandRepositoryStub(),
            evaluation_service=_EvaluationServiceStub(),
            clock=_ClockStub(),
            uuid_generator=_UuidStub(uuid4()),
        )
        with self.assertRaises(SegmentVersionActiveVersionNotFoundError):
            await missing_active_use_case(
                CreateSegmentSnapshotCommand(
                    tenant_id=tenant_id,
                    segment_id=segment_id,
                )
            )

    async def test_create_snapshot_marks_failed_on_controlled_error(self) -> None:
        tenant_id = EntityIdVO.from_value(uuid4())
        segment_id = SegmentIdVO.from_value(uuid4())
        version = _version(segment_id)
        snapshot_command = _SnapshotCommandRepositoryStub()
        member_command = _MemberCommandRepositoryStub()
        use_case = CreateSegmentSnapshotUseCase(
            segment_repository=_SegmentRepositoryStub(_segment(segment_id)),
            version_repository=_VersionRepositoryStub(version),
            snapshot_command_repository=snapshot_command,
            snapshot_query_repository=_SnapshotQueryRepositoryStub(),
            member_command_repository=member_command,
            evaluation_service=_EvaluationServiceStub(
                exc=SegmentVersionEvaluationError("invalid")
            ),
            clock=_ClockStub(),
            uuid_generator=_UuidStub(uuid4()),
        )

        with self.assertRaises(SegmentVersionEvaluationError):
            await use_case(
                CreateSegmentSnapshotCommand(
                    tenant_id=tenant_id,
                    segment_id=segment_id,
                )
            )

        self.assertEqual(
            snapshot_command.saved[-1].status, SegmentSnapshotStatusVO.FAILED
        )
        self.assertEqual(
            snapshot_command.saved[-1].error_code,
            "SegmentVersionEvaluationError",
        )
        self.assertEqual(
            member_command.deleted_snapshot_ids,
            [snapshot_command.saved[0].segment_snapshot_id],
        )

    async def test_get_list_and_members_use_cases(self) -> None:
        tenant_id = EntityIdVO.from_value(uuid4())
        segment_id = SegmentIdVO.from_value(uuid4())
        snapshot_id = SegmentSnapshotIdVO.from_value(uuid4())
        contact_id = uuid4()
        now = datetime(2026, 5, 28, 12, 0, tzinfo=UTC)
        snapshot_dto = SegmentSnapshotDTO(
            id=snapshot_id.uuid,
            segment_id=segment_id.uuid,
            segment_version_id=uuid4(),
            status="completed",
            member_count=1,
            started_at=now,
            completed_at=now,
            error_code=None,
            error_message=None,
            created_at=now,
            updated_at=now,
        )
        snapshot_query = _SnapshotQueryRepositoryStub()
        snapshot_query.snapshot = SegmentSnapshot.create(
            segment_snapshot_id=snapshot_id,
            segment_id=segment_id,
            segment_version_id=SegmentVersionIdVO.from_value(
                snapshot_dto.segment_version_id
            ),
            status=SegmentSnapshotStatusVO.COMPLETED,
            member_count=1,
            started_at=now,
            completed_at=now,
        )
        snapshot_query.items = [snapshot_dto]

        get_result = await GetSegmentSnapshotUseCase(repository=snapshot_query)(
            GetSegmentSnapshotQuery(
                tenant_id=tenant_id,
                segment_snapshot_id=snapshot_id,
            )
        )
        list_result = await ListSegmentSnapshotsUseCase(
            segment_repository=_SegmentRepositoryStub(_segment(segment_id)),
            repository=snapshot_query,
        )(
            ListSegmentSnapshotsQuery(
                tenant_id=tenant_id,
                segment_id=segment_id,
            )
        )

        member_item = SegmentSnapshotMemberDTO(
            id=uuid4(),
            segment_snapshot_id=snapshot_id.uuid,
            contact_id=contact_id,
            position=0,
            created_at=now,
        )
        member_result = await ListSegmentSnapshotMembersUseCase(
            snapshot_repository=snapshot_query,
            member_repository=_MemberQueryRepositoryStub([member_item]),
            contact_lookup=_ContactLookupStub(
                {
                    contact_id: ContactSummaryDTO(
                        id=contact_id,
                        first_name="Denis",
                        last_name=None,
                        middle_name=None,
                        status="active",
                    )
                }
            ),
        )(
            ListSegmentSnapshotMembersQuery(
                tenant_id=tenant_id,
                segment_snapshot_id=snapshot_id,
            )
        )

        self.assertEqual(get_result.id, snapshot_id.uuid)
        self.assertEqual(list_result, [snapshot_dto])
        self.assertEqual(member_result[0].contact.first_name, "Denis")

    async def test_get_snapshot_raises_not_found(self) -> None:
        with self.assertRaises(SegmentSnapshotNotFoundError):
            await GetSegmentSnapshotUseCase(repository=_SnapshotQueryRepositoryStub())(
                GetSegmentSnapshotQuery(
                    tenant_id=EntityIdVO.from_value(uuid4()),
                    segment_snapshot_id=SegmentSnapshotIdVO.from_value(uuid4()),
                )
            )


__all__ = ["SegmentationSnapshotUseCaseTests"]
