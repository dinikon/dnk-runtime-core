from __future__ import annotations

import unittest
from datetime import UTC, datetime
from uuid import UUID, uuid4

from src.modules.segmentation.application.segment_static_member import (
    AddStaticMemberCommand,
    AddStaticMemberUseCase,
    ContactSummaryDTO,
    ListStaticMembersQuery,
    ListStaticMembersUseCase,
    RemoveStaticMemberCommand,
    RemoveStaticMemberUseCase,
    StaticMemberDTO,
)
from src.modules.segmentation.domain.segment_definition import (
    SegmentDefinition,
    SegmentIdVO,
    SegmentKindVO,
    SegmentStatusVO,
)
from src.modules.segmentation.domain.segment_static_member import (
    SegmentStaticMember,
    SegmentStaticMemberArchivedSegmentError,
    SegmentStaticMemberContactNotFoundError,
    SegmentStaticMemberError,
    SegmentStaticMemberIdVO,
    SegmentStaticMemberNonStaticSegmentError,
    SegmentStaticMemberSourceTypeVO,
)
from src.modules.shared import EntityIdVO


class _UuidGeneratorStub:
    def __init__(self, *values: UUID) -> None:
        self._values = list(values)

    def new_uuid(self) -> UUID:
        return self._values.pop(0)


class _SegmentDefinitionRepositoryStub:
    def __init__(self, segment: SegmentDefinition | None) -> None:
        self.segment = segment
        self.loads: list[tuple[EntityIdVO, SegmentIdVO]] = []

    async def load(self, *, tenant_id: EntityIdVO, segment_id: SegmentIdVO):
        self.loads.append((tenant_id, segment_id))
        return self.segment


class _StaticMemberRepositoryStub:
    def __init__(self) -> None:
        self.members: dict[tuple[UUID, UUID], SegmentStaticMember] = {}
        self.created_at = datetime(2026, 5, 28, 12, 0, tzinfo=UTC)

    async def exists(
        self,
        *,
        tenant_id: EntityIdVO,
        segment_id: SegmentIdVO,
        contact_id: EntityIdVO,
    ) -> bool:
        return (segment_id.uuid, contact_id.uuid) in self.members

    async def add(
        self,
        *,
        tenant_id: EntityIdVO,
        member: SegmentStaticMember,
    ) -> SegmentStaticMember:
        key = (member.segment_id.uuid, member.contact_id.uuid)
        if key not in self.members:
            self.members[key] = member
        return self.members[key]

    async def remove(
        self,
        *,
        tenant_id: EntityIdVO,
        segment_id: SegmentIdVO,
        contact_id: EntityIdVO,
    ) -> bool:
        return self.members.pop((segment_id.uuid, contact_id.uuid), None) is not None

    async def get(
        self,
        *,
        tenant_id: EntityIdVO,
        segment_id: SegmentIdVO,
        contact_id: EntityIdVO,
    ) -> StaticMemberDTO | None:
        member = self.members.get((segment_id.uuid, contact_id.uuid))
        if member is None:
            return None
        return StaticMemberDTO(
            id=member.segment_static_member_id.uuid,
            segment_id=member.segment_id.uuid,
            contact_id=member.contact_id.uuid,
            source_type=member.source_type.value,
            metadata=None if member.metadata is None else dict(member.metadata),
            created_at=self.created_at,
            updated_at=self.created_at,
        )

    async def list(
        self,
        *,
        tenant_id: EntityIdVO,
        segment_id: SegmentIdVO,
        limit: int,
        offset: int,
    ) -> list[StaticMemberDTO]:
        items = [
            await self.get(
                tenant_id=tenant_id,
                segment_id=member.segment_id,
                contact_id=member.contact_id,
            )
            for member in self.members.values()
            if member.segment_id == segment_id
        ]
        return [item for item in items if item is not None][offset : offset + limit]


class _ContactLookupStub:
    def __init__(self, *, exists: bool = True) -> None:
        self.exists_value = exists
        self.exists_calls = 0
        self.summary = ContactSummaryDTO(
            id=uuid4(),
            first_name="Denis",
            last_name=None,
            middle_name=None,
            status="active",
        )
        self.batch_calls: list[tuple[UUID, ...]] = []

    async def exists(self, *, tenant_id: EntityIdVO, contact_id: EntityIdVO) -> bool:
        self.exists_calls += 1
        return self.exists_value

    async def get_summary(
        self,
        *,
        tenant_id: EntityIdVO,
        contact_id: EntityIdVO,
    ) -> ContactSummaryDTO | None:
        return ContactSummaryDTO(
            id=contact_id.uuid,
            first_name=self.summary.first_name,
            last_name=self.summary.last_name,
            middle_name=self.summary.middle_name,
            status=self.summary.status,
        )

    async def get_summaries(
        self,
        *,
        tenant_id: EntityIdVO,
        contact_ids: list[EntityIdVO],
    ) -> dict[UUID, ContactSummaryDTO]:
        self.batch_calls.append(tuple(contact_id.uuid for contact_id in contact_ids))
        return {
            contact_id.uuid: ContactSummaryDTO(
                id=contact_id.uuid,
                first_name="Denis",
                last_name=None,
                middle_name=None,
                status="active",
            )
            for contact_id in contact_ids
        }


def _segment(
    *,
    segment_id: SegmentIdVO,
    kind: SegmentKindVO = SegmentKindVO.STATIC,
    status: SegmentStatusVO = SegmentStatusVO.ACTIVE,
) -> SegmentDefinition:
    return SegmentDefinition(
        segment_id=segment_id,
        name="VIP",
        segment_kind=kind,
        status=status,
    )


class SegmentationStaticMemberUseCaseTests(unittest.IsolatedAsyncioTestCase):

    def test_static_member_entity_copies_metadata(self) -> None:
        metadata = {"nested": {"source": "test"}}
        member = SegmentStaticMember.create(
            segment_static_member_id=SegmentStaticMemberIdVO.from_value(uuid4()),
            segment_id=SegmentIdVO.from_value(uuid4()),
            contact_id=EntityIdVO.from_value(uuid4()),
            source_type=SegmentStaticMemberSourceTypeVO.API,
            metadata=metadata,
        )

        metadata["nested"]["source"] = "changed"

        self.assertEqual(member.metadata["nested"]["source"], "test")
        with self.assertRaises(SegmentStaticMemberError):
            SegmentStaticMember.create(
                segment_static_member_id=SegmentStaticMemberIdVO.from_value(uuid4()),
                segment_id=SegmentIdVO.from_value(uuid4()),
                contact_id=EntityIdVO.from_value(uuid4()),
                source_type=SegmentStaticMemberSourceTypeVO.API,
                metadata=[],
            )

    async def test_add_static_member_is_idempotent_for_duplicate_contact(self) -> None:
        tenant_id = EntityIdVO.from_value(uuid4())
        segment_id = SegmentIdVO.from_value(uuid4())
        contact_id = EntityIdVO.from_value(uuid4())
        member_id = uuid4()
        repositories = _StaticMemberRepositoryStub()
        use_case = AddStaticMemberUseCase(
            segment_repository=_SegmentDefinitionRepositoryStub(
                _segment(segment_id=segment_id)
            ),
            member_command_repository=repositories,
            member_query_repository=repositories,
            contact_lookup=_ContactLookupStub(),
            uuid_generator=_UuidGeneratorStub(member_id, uuid4()),
        )
        command = AddStaticMemberCommand(
            tenant_id=tenant_id,
            segment_id=segment_id,
            contact_id=contact_id,
            source_type=SegmentStaticMemberSourceTypeVO.MANUAL,
            metadata={"source": "test"},
        )

        first = await use_case(command)
        second = await use_case(command)

        self.assertEqual(first.id, member_id)
        self.assertEqual(second.id, member_id)
        self.assertEqual(len(repositories.members), 1)
        self.assertIsNotNone(second.contact)
        self.assertEqual(second.contact.id, contact_id.uuid)

    async def test_add_static_member_rejects_missing_contact(self) -> None:
        tenant_id = EntityIdVO.from_value(uuid4())
        segment_id = SegmentIdVO.from_value(uuid4())
        contact_id = EntityIdVO.from_value(uuid4())
        use_case = AddStaticMemberUseCase(
            segment_repository=_SegmentDefinitionRepositoryStub(
                _segment(segment_id=segment_id)
            ),
            member_command_repository=_StaticMemberRepositoryStub(),
            member_query_repository=_StaticMemberRepositoryStub(),
            contact_lookup=_ContactLookupStub(exists=False),
            uuid_generator=_UuidGeneratorStub(uuid4()),
        )

        with self.assertRaises(SegmentStaticMemberContactNotFoundError):
            await use_case(
                AddStaticMemberCommand(
                    tenant_id=tenant_id,
                    segment_id=segment_id,
                    contact_id=contact_id,
                )
            )

    async def test_add_static_member_rejects_dynamic_segment(self) -> None:
        tenant_id = EntityIdVO.from_value(uuid4())
        segment_id = SegmentIdVO.from_value(uuid4())
        contact_lookup = _ContactLookupStub()
        use_case = AddStaticMemberUseCase(
            segment_repository=_SegmentDefinitionRepositoryStub(
                _segment(segment_id=segment_id, kind=SegmentKindVO.DYNAMIC)
            ),
            member_command_repository=_StaticMemberRepositoryStub(),
            member_query_repository=_StaticMemberRepositoryStub(),
            contact_lookup=contact_lookup,
            uuid_generator=_UuidGeneratorStub(uuid4()),
        )

        with self.assertRaises(SegmentStaticMemberNonStaticSegmentError):
            await use_case(
                AddStaticMemberCommand(
                    tenant_id=tenant_id,
                    segment_id=segment_id,
                    contact_id=EntityIdVO.from_value(uuid4()),
                )
            )
        self.assertEqual(contact_lookup.exists_calls, 0)

    async def test_add_static_member_rejects_archived_segment(self) -> None:
        tenant_id = EntityIdVO.from_value(uuid4())
        segment_id = SegmentIdVO.from_value(uuid4())
        use_case = AddStaticMemberUseCase(
            segment_repository=_SegmentDefinitionRepositoryStub(
                _segment(segment_id=segment_id, status=SegmentStatusVO.ARCHIVED)
            ),
            member_command_repository=_StaticMemberRepositoryStub(),
            member_query_repository=_StaticMemberRepositoryStub(),
            contact_lookup=_ContactLookupStub(),
            uuid_generator=_UuidGeneratorStub(uuid4()),
        )

        with self.assertRaises(SegmentStaticMemberArchivedSegmentError):
            await use_case(
                AddStaticMemberCommand(
                    tenant_id=tenant_id,
                    segment_id=segment_id,
                    contact_id=EntityIdVO.from_value(uuid4()),
                )
            )

    async def test_remove_absent_static_member_is_idempotent(self) -> None:
        tenant_id = EntityIdVO.from_value(uuid4())
        segment_id = SegmentIdVO.from_value(uuid4())
        repository = _StaticMemberRepositoryStub()
        use_case = RemoveStaticMemberUseCase(
            segment_repository=_SegmentDefinitionRepositoryStub(
                _segment(segment_id=segment_id)
            ),
            member_repository=repository,
        )

        removed = await use_case(
            RemoveStaticMemberCommand(
                tenant_id=tenant_id,
                segment_id=segment_id,
                contact_id=EntityIdVO.from_value(uuid4()),
            )
        )

        self.assertFalse(removed)

    async def test_list_static_members_enriches_contact_summaries_when_requested(
        self,
    ) -> None:
        tenant_id = EntityIdVO.from_value(uuid4())
        segment_id = SegmentIdVO.from_value(uuid4())
        contact_id = EntityIdVO.from_value(uuid4())
        repository = _StaticMemberRepositoryStub()
        await repository.add(
            tenant_id=tenant_id,
            member=SegmentStaticMember.create(
                segment_static_member_id=SegmentStaticMemberIdVO.from_value(uuid4()),
                segment_id=segment_id,
                contact_id=contact_id,
                source_type=SegmentStaticMemberSourceTypeVO.API,
            ),
        )
        contact_lookup = _ContactLookupStub()
        use_case = ListStaticMembersUseCase(
            repository=repository,
            contact_lookup=contact_lookup,
        )

        result = await use_case(
            ListStaticMembersQuery(
                tenant_id=tenant_id,
                segment_id=segment_id,
                include_contact_summary=True,
            )
        )

        self.assertEqual(result[0].contact.id, contact_id.uuid)
        self.assertEqual(contact_lookup.batch_calls, [(contact_id.uuid,)])

    async def test_list_static_members_can_skip_contact_summaries(self) -> None:
        tenant_id = EntityIdVO.from_value(uuid4())
        segment_id = SegmentIdVO.from_value(uuid4())
        repository = _StaticMemberRepositoryStub()
        await repository.add(
            tenant_id=tenant_id,
            member=SegmentStaticMember.create(
                segment_static_member_id=SegmentStaticMemberIdVO.from_value(uuid4()),
                segment_id=segment_id,
                contact_id=EntityIdVO.from_value(uuid4()),
                source_type=SegmentStaticMemberSourceTypeVO.API,
            ),
        )
        contact_lookup = _ContactLookupStub()
        use_case = ListStaticMembersUseCase(
            repository=repository,
            contact_lookup=contact_lookup,
        )

        result = await use_case(
            ListStaticMembersQuery(
                tenant_id=tenant_id,
                segment_id=segment_id,
                include_contact_summary=False,
            )
        )

        self.assertIsNone(result[0].contact)
        self.assertEqual(contact_lookup.batch_calls, [])


__all__ = ["SegmentationStaticMemberUseCaseTests"]
