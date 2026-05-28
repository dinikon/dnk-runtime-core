from __future__ import annotations

import hashlib
import unittest
from datetime import UTC, datetime
from uuid import UUID, uuid4

from src.modules.segmentation.application.segment_version import (
    ActivateSegmentVersionCommand,
    ActivateSegmentVersionUseCase,
    CreateSegmentVersionCommand,
    CreateSegmentVersionUseCase,
    GetSegmentVersionQuery,
    GetSegmentVersionUseCase,
    ListSegmentVersionsQuery,
    ListSegmentVersionsUseCase,
    SegmentVersionDTO,
)
from src.modules.segmentation.domain.segment_definition import (
    SegmentDefinition,
    SegmentDefinitionArchivedError,
    SegmentIdVO,
    SegmentKindVO,
    SegmentStatusVO,
)
from src.modules.segmentation.domain.segment_version import (
    SegmentVersion,
    SegmentVersionIdVO,
    SegmentVersionNotFoundError,
    SegmentVersionStatusVO,
)
from src.modules.shared import EntityIdVO


class _UuidGeneratorStub:
    def __init__(self, *values: UUID) -> None:
        self._values = list(values)

    def new_uuid(self) -> UUID:
        return self._values.pop(0)


class _ClockStub:
    def __init__(self, now: datetime) -> None:
        self._now = now

    def now(self) -> datetime:
        return self._now


class _SegmentDefinitionRepositoryStub:
    def __init__(self, segment: SegmentDefinition | None) -> None:
        self.segment = segment

    async def load(self, *, tenant_id: EntityIdVO, segment_id: SegmentIdVO):
        return self.segment


class _SegmentVersionRepositoryStub:
    def __init__(self, *versions: SegmentVersion) -> None:
        self.versions = {
            version.segment_version_id.uuid: version for version in versions
        }
        self.saved: list[SegmentVersion] = []
        self.archived_active_calls: list[tuple[SegmentIdVO, datetime]] = []
        self.next_version_number = 1
        self.last_list: tuple[int, int] | None = None
        self.created_at = datetime(2026, 5, 28, 12, 0, tzinfo=UTC)

    async def load(
        self,
        *,
        tenant_id: EntityIdVO,
        segment_version_id: SegmentVersionIdVO,
    ) -> SegmentVersion | None:
        return self.versions.get(segment_version_id.uuid)

    async def get_active(
        self,
        *,
        tenant_id: EntityIdVO,
        segment_id: SegmentIdVO,
    ) -> SegmentVersion | None:
        for version in self.versions.values():
            if (
                version.segment_id == segment_id
                and version.status == SegmentVersionStatusVO.ACTIVE
            ):
                return version
        return None

    async def get_next_version_number(
        self,
        *,
        tenant_id: EntityIdVO,
        segment_id: SegmentIdVO,
    ) -> int:
        return self.next_version_number

    async def save(
        self,
        *,
        tenant_id: EntityIdVO,
        version: SegmentVersion,
    ) -> SegmentVersion:
        self.saved.append(version)
        self.versions[version.segment_version_id.uuid] = version
        return version

    async def archive_active_versions(
        self,
        *,
        tenant_id: EntityIdVO,
        segment_id: SegmentIdVO,
        now: datetime,
    ) -> None:
        self.archived_active_calls.append((segment_id, now))

    async def get(
        self,
        *,
        tenant_id: EntityIdVO,
        segment_id: SegmentIdVO,
        segment_version_id: SegmentVersionIdVO,
    ) -> SegmentVersionDTO | None:
        version = self.versions.get(segment_version_id.uuid)
        if version is None or version.segment_id != segment_id:
            return None
        return self._to_dto(version)

    async def list(
        self,
        *,
        tenant_id: EntityIdVO,
        segment_id: SegmentIdVO,
        limit: int,
        offset: int,
    ) -> list[SegmentVersionDTO]:
        self.last_list = (limit, offset)
        items = [
            version
            for version in self.versions.values()
            if version.segment_id == segment_id
        ][offset : offset + limit]
        return [self._to_dto(version) for version in items]

    def _to_dto(self, version: SegmentVersion) -> SegmentVersionDTO:
        return SegmentVersionDTO(
            id=version.segment_version_id.uuid,
            segment_id=version.segment_id.uuid,
            version_number=version.version_number,
            status=version.status.value,
            config=dict(version.config),
            config_checksum=version.config_checksum,
            activated_at=version.activated_at,
            archived_at=version.archived_at,
            created_at=self.created_at,
            updated_at=self.created_at,
        )


def _segment(
    *,
    segment_id: SegmentIdVO,
    status: SegmentStatusVO = SegmentStatusVO.ACTIVE,
) -> SegmentDefinition:
    return SegmentDefinition(
        segment_id=segment_id,
        name="VIP",
        segment_kind=SegmentKindVO.STATIC,
        status=status,
    )


def _version(
    *,
    segment_id: SegmentIdVO,
    version_id: SegmentVersionIdVO | None = None,
    status: SegmentVersionStatusVO = SegmentVersionStatusVO.DRAFT,
    version_number: int = 1,
) -> SegmentVersion:
    return SegmentVersion(
        segment_version_id=version_id or SegmentVersionIdVO.from_value(uuid4()),
        segment_id=segment_id,
        version_number=version_number,
        status=status,
        config={"a": 1},
        config_checksum="abc",
    )


class SegmentationSegmentVersionUseCaseTests(unittest.IsolatedAsyncioTestCase):
    async def test_create_segment_version_computes_checksum_and_next_number(
        self,
    ) -> None:
        tenant_id = EntityIdVO.from_value(uuid4())
        segment_id = SegmentIdVO.from_value(uuid4())
        version_id = uuid4()
        version_repository = _SegmentVersionRepositoryStub()
        version_repository.next_version_number = 3
        use_case = CreateSegmentVersionUseCase(
            segment_repository=_SegmentDefinitionRepositoryStub(
                _segment(segment_id=segment_id)
            ),
            version_command_repository=version_repository,
            version_query_repository=version_repository,
            uuid_generator=_UuidGeneratorStub(version_id),
        )

        result = await use_case(
            CreateSegmentVersionCommand(
                tenant_id=tenant_id,
                segment_id=segment_id,
                config={"b": 2, "a": 1},
            )
        )

        expected_checksum = hashlib.sha256(b'{"a":1,"b":2}').hexdigest()
        self.assertEqual(result.id, version_id)
        self.assertEqual(result.version_number, 3)
        self.assertEqual(result.config_checksum, expected_checksum)
        self.assertEqual(
            version_repository.saved[0].status, SegmentVersionStatusVO.DRAFT
        )

    async def test_create_segment_version_rejects_archived_segment(self) -> None:
        segment_id = SegmentIdVO.from_value(uuid4())
        use_case = CreateSegmentVersionUseCase(
            segment_repository=_SegmentDefinitionRepositoryStub(
                _segment(segment_id=segment_id, status=SegmentStatusVO.ARCHIVED)
            ),
            version_command_repository=_SegmentVersionRepositoryStub(),
            version_query_repository=_SegmentVersionRepositoryStub(),
            uuid_generator=_UuidGeneratorStub(uuid4()),
        )

        with self.assertRaises(SegmentDefinitionArchivedError):
            await use_case(
                CreateSegmentVersionCommand(
                    tenant_id=EntityIdVO.from_value(uuid4()),
                    segment_id=segment_id,
                    config={},
                )
            )

    async def test_activate_segment_version_archives_previous_active_versions(
        self,
    ) -> None:
        tenant_id = EntityIdVO.from_value(uuid4())
        now = datetime(2026, 5, 28, 12, 0, tzinfo=UTC)
        segment_id = SegmentIdVO.from_value(uuid4())
        version_id = SegmentVersionIdVO.from_value(uuid4())
        version_repository = _SegmentVersionRepositoryStub(
            _version(segment_id=segment_id, version_id=version_id)
        )
        use_case = ActivateSegmentVersionUseCase(
            segment_repository=_SegmentDefinitionRepositoryStub(
                _segment(segment_id=segment_id)
            ),
            version_command_repository=version_repository,
            version_query_repository=version_repository,
            clock=_ClockStub(now),
        )

        result = await use_case(
            ActivateSegmentVersionCommand(
                tenant_id=tenant_id,
                segment_id=segment_id,
                segment_version_id=version_id,
            )
        )

        self.assertEqual(result.status, SegmentVersionStatusVO.ACTIVE.value)
        self.assertEqual(result.activated_at, now)
        self.assertEqual(version_repository.archived_active_calls, [(segment_id, now)])

    async def test_activate_segment_version_rejects_mismatched_segment(self) -> None:
        real_segment_id = SegmentIdVO.from_value(uuid4())
        requested_segment_id = SegmentIdVO.from_value(uuid4())
        version_id = SegmentVersionIdVO.from_value(uuid4())
        use_case = ActivateSegmentVersionUseCase(
            segment_repository=_SegmentDefinitionRepositoryStub(
                _segment(segment_id=requested_segment_id)
            ),
            version_command_repository=_SegmentVersionRepositoryStub(
                _version(segment_id=real_segment_id, version_id=version_id)
            ),
            version_query_repository=_SegmentVersionRepositoryStub(),
            clock=_ClockStub(datetime(2026, 5, 28, 12, 0, tzinfo=UTC)),
        )

        with self.assertRaises(SegmentVersionNotFoundError):
            await use_case(
                ActivateSegmentVersionCommand(
                    tenant_id=EntityIdVO.from_value(uuid4()),
                    segment_id=requested_segment_id,
                    segment_version_id=version_id,
                )
            )

    async def test_get_and_list_segment_versions_use_query_repository(self) -> None:
        tenant_id = EntityIdVO.from_value(uuid4())
        segment_id = SegmentIdVO.from_value(uuid4())
        version_id = SegmentVersionIdVO.from_value(uuid4())
        repository = _SegmentVersionRepositoryStub(
            _version(segment_id=segment_id, version_id=version_id)
        )

        found = await GetSegmentVersionUseCase(repository=repository)(
            GetSegmentVersionQuery(
                tenant_id=tenant_id,
                segment_id=segment_id,
                segment_version_id=version_id,
            )
        )
        page = await ListSegmentVersionsUseCase(repository=repository)(
            ListSegmentVersionsQuery(
                tenant_id=tenant_id,
                segment_id=segment_id,
                limit=10,
                offset=5,
            )
        )

        self.assertEqual(found.id, version_id.uuid)
        self.assertEqual(repository.last_list, (10, 5))
        self.assertEqual(page, [])


__all__ = ["SegmentationSegmentVersionUseCaseTests"]
