from dataclasses import replace
from typing import Protocol

from src.modules.segmentation.application.segment_static_member.command import (
    AddStaticMemberCommand,
)
from src.modules.segmentation.application.segment_static_member.dto import (
    StaticMemberDTO,
)
from src.modules.segmentation.application.segment_static_member.query import (
    ContactLookupProtocol,
    SegmentStaticMemberQueryRepositoryProtocol,
)
from src.modules.segmentation.domain.segment_definition import (
    SegmentDefinition,
    SegmentDefinitionCommandRepositoryProtocol,
    SegmentDefinitionNotFoundError,
    SegmentKindVO,
    SegmentStatusVO,
)
from src.modules.segmentation.domain.segment_static_member import (
    SegmentStaticMember,
    SegmentStaticMemberArchivedSegmentError,
    SegmentStaticMemberCommandRepositoryProtocol,
    SegmentStaticMemberContactNotFoundError,
    SegmentStaticMemberError,
    SegmentStaticMemberIdVO,
    SegmentStaticMemberNonStaticSegmentError,
    SegmentStaticMemberSourceTypeVO,
)
from src.modules.shared import UUIdGeneratorProtocol


class AddStaticMemberUseCaseProtocol(Protocol):
    """Use case port for adding static segment member."""

    async def __call__(self, command: AddStaticMemberCommand) -> StaticMemberDTO:
        """Adds Contact to static segment idempotently."""
        ...


class AddStaticMemberUseCase:
    """Adds Contact to a static segment."""

    def __init__(
        self,
        *,
        segment_repository: SegmentDefinitionCommandRepositoryProtocol,
        member_command_repository: SegmentStaticMemberCommandRepositoryProtocol,
        member_query_repository: SegmentStaticMemberQueryRepositoryProtocol,
        contact_lookup: ContactLookupProtocol,
        uuid_generator: UUIdGeneratorProtocol,
    ) -> None:
        self._segment_repository = segment_repository
        self._member_command_repository = member_command_repository
        self._member_query_repository = member_query_repository
        self._contact_lookup = contact_lookup
        self._uuid_generator = uuid_generator

    async def __call__(self, command: AddStaticMemberCommand) -> StaticMemberDTO:
        segment = await self._segment_repository.load(
            tenant_id=command.tenant_id,
            segment_id=command.segment_id,
        )
        if segment is None:
            raise SegmentDefinitionNotFoundError(str(command.segment_id))
        self._ensure_segment_can_change_members(segment)

        contact_exists = await self._contact_lookup.exists(
            tenant_id=command.tenant_id,
            contact_id=command.contact_id,
        )
        if not contact_exists:
            raise SegmentStaticMemberContactNotFoundError(str(command.contact_id))

        metadata = None if command.metadata is None else dict(command.metadata)
        member = SegmentStaticMember.create(
            segment_static_member_id=SegmentStaticMemberIdVO.from_value(
                self._uuid_generator.new()
            ),
            segment_id=command.segment_id,
            contact_id=command.contact_id,
            source_type=SegmentStaticMemberSourceTypeVO(command.source_type),
            metadata=metadata,
        )
        saved = await self._member_command_repository.add(
            tenant_id=command.tenant_id,
            member=member,
        )
        dto = await self._member_query_repository.get(
            tenant_id=command.tenant_id,
            segment_id=saved.segment_id,
            contact_id=saved.contact_id,
        )
        if dto is None:
            raise SegmentStaticMemberError(
                "Static member was saved but could not be loaded."
            )
        contact = await self._contact_lookup.get_summary(
            tenant_id=command.tenant_id,
            contact_id=saved.contact_id,
        )
        return replace(dto, contact=contact)

    @staticmethod
    def _ensure_segment_can_change_members(segment: SegmentDefinition) -> None:
        if segment.status == SegmentStatusVO.ARCHIVED:
            raise SegmentStaticMemberArchivedSegmentError(str(segment.segment_id))
        if segment.segment_kind != SegmentKindVO.STATIC:
            raise SegmentStaticMemberNonStaticSegmentError(str(segment.segment_id))


__all__ = [
    "AddStaticMemberUseCase",
    "AddStaticMemberUseCaseProtocol",
]
