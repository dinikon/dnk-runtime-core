from __future__ import annotations

import unittest
from datetime import UTC, datetime
from uuid import UUID, uuid4

from src.modules.segmentation.application.segment_definition import (
    ArchiveSegmentDefinitionCommand,
    ArchiveSegmentDefinitionUseCase,
    CreateSegmentDefinitionCommand,
    CreateSegmentDefinitionUseCase,
    GetSegmentDefinitionQuery,
    GetSegmentDefinitionUseCase,
    ListSegmentDefinitionsQuery,
    ListSegmentDefinitionsUseCase,
    SegmentDefinitionDTO,
    UpdateSegmentDefinitionCommand,
    UpdateSegmentDefinitionUseCase,
)
from src.modules.segmentation.domain.segment_definition import (
    SegmentDefinition,
    SegmentDefinitionNotFoundError,
    SegmentIdVO,
    SegmentKindVO,
    SegmentStatusVO,
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
    def __init__(self, *segments: SegmentDefinition) -> None:
        self.segments = {segment.segment_id.uuid: segment for segment in segments}
        self.saved: list[SegmentDefinition] = []
        self.last_list: tuple[int, int] | None = None
        self.created_at = datetime(2026, 5, 28, 12, 0, tzinfo=UTC)

    async def load(self, *, tenant_id: EntityIdVO, segment_id: SegmentIdVO):
        return self.segments.get(segment_id.uuid)

    async def save(
        self,
        *,
        tenant_id: EntityIdVO,
        segment: SegmentDefinition,
    ) -> SegmentDefinition:
        self.saved.append(segment)
        self.segments[segment.segment_id.uuid] = segment
        return segment

    async def get(
        self,
        *,
        tenant_id: EntityIdVO,
        segment_id: SegmentIdVO,
    ) -> SegmentDefinitionDTO | None:
        segment = self.segments.get(segment_id.uuid)
        if segment is None:
            return None
        return SegmentDefinitionDTO(
            id=segment.segment_id.uuid,
            name=segment.name,
            segment_kind=segment.segment_kind.value,
            status=segment.status.value,
            description=segment.description,
            archived_at=segment.archived_at,
            created_at=self.created_at,
            updated_at=self.created_at,
        )

    async def list(
        self,
        *,
        tenant_id: EntityIdVO,
        limit: int,
        offset: int,
    ) -> list[SegmentDefinitionDTO]:
        self.last_list = (limit, offset)
        items = list(self.segments.values())[offset : offset + limit]
        return [
            SegmentDefinitionDTO(
                id=segment.segment_id.uuid,
                name=segment.name,
                segment_kind=segment.segment_kind.value,
                status=segment.status.value,
                description=segment.description,
                archived_at=segment.archived_at,
                created_at=self.created_at,
                updated_at=self.created_at,
            )
            for segment in items
        ]


def _segment(
    *,
    segment_id: SegmentIdVO | None = None,
    name: str = "VIP",
    kind: SegmentKindVO = SegmentKindVO.STATIC,
    status: SegmentStatusVO = SegmentStatusVO.ACTIVE,
) -> SegmentDefinition:
    return SegmentDefinition(
        segment_id=segment_id or SegmentIdVO.from_value(uuid4()),
        name=name,
        segment_kind=kind,
        status=status,
    )


class SegmentationSegmentDefinitionUseCaseTests(unittest.IsolatedAsyncioTestCase):
    async def test_create_segment_definition_generates_id_and_returns_dto(self) -> None:
        tenant_id = EntityIdVO.from_value(uuid4())
        segment_uuid = uuid4()
        repository = _SegmentDefinitionRepositoryStub()
        use_case = CreateSegmentDefinitionUseCase(
            command_repository=repository,
            query_repository=repository,
            uuid_generator=_UuidGeneratorStub(segment_uuid),
        )

        result = await use_case(
            CreateSegmentDefinitionCommand(
                tenant_id=tenant_id,
                name=" VIP ",
                segment_kind=SegmentKindVO.STATIC,
                description="Top customers",
            )
        )

        self.assertEqual(result.id, segment_uuid)
        self.assertEqual(result.name, "VIP")
        self.assertEqual(repository.saved[0].segment_kind, SegmentKindVO.STATIC)

    async def test_update_segment_definition_changes_name_and_description(self) -> None:
        tenant_id = EntityIdVO.from_value(uuid4())
        segment_id = SegmentIdVO.from_value(uuid4())
        repository = _SegmentDefinitionRepositoryStub(_segment(segment_id=segment_id))
        use_case = UpdateSegmentDefinitionUseCase(
            command_repository=repository,
            query_repository=repository,
        )

        result = await use_case(
            UpdateSegmentDefinitionCommand(
                tenant_id=tenant_id,
                segment_id=segment_id,
                name=" VIP 2 ",
                description=None,
                description_provided=True,
            )
        )

        self.assertEqual(result.name, "VIP 2")
        self.assertIsNone(result.description)

    async def test_archive_segment_definition_is_idempotent(self) -> None:
        tenant_id = EntityIdVO.from_value(uuid4())
        segment_id = SegmentIdVO.from_value(uuid4())
        now = datetime(2026, 5, 28, 12, 0, tzinfo=UTC)
        repository = _SegmentDefinitionRepositoryStub(_segment(segment_id=segment_id))
        use_case = ArchiveSegmentDefinitionUseCase(
            command_repository=repository,
            query_repository=repository,
            clock=_ClockStub(now),
        )

        first = await use_case(
            ArchiveSegmentDefinitionCommand(
                tenant_id=tenant_id,
                segment_id=segment_id,
            )
        )
        second = await use_case(
            ArchiveSegmentDefinitionCommand(
                tenant_id=tenant_id,
                segment_id=segment_id,
            )
        )

        self.assertEqual(first.status, SegmentStatusVO.ARCHIVED.value)
        self.assertEqual(second.archived_at, now)

    async def test_get_segment_definition_raises_not_found(self) -> None:
        use_case = GetSegmentDefinitionUseCase(
            repository=_SegmentDefinitionRepositoryStub()
        )

        with self.assertRaises(SegmentDefinitionNotFoundError):
            await use_case(
                GetSegmentDefinitionQuery(
                    tenant_id=EntityIdVO.from_value(uuid4()),
                    segment_id=SegmentIdVO.from_value(uuid4()),
                )
            )

    async def test_list_segment_definitions_passes_pagination(self) -> None:
        tenant_id = EntityIdVO.from_value(uuid4())
        repository = _SegmentDefinitionRepositoryStub(_segment())
        use_case = ListSegmentDefinitionsUseCase(repository=repository)

        result = await use_case(
            ListSegmentDefinitionsQuery(
                tenant_id=tenant_id,
                limit=10,
                offset=5,
            )
        )

        self.assertEqual(repository.last_list, (10, 5))
        self.assertEqual(len(result), 0)


__all__ = ["SegmentationSegmentDefinitionUseCaseTests"]
