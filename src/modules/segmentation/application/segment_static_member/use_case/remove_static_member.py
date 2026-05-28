from typing import Protocol

from src.modules.segmentation.application.segment_static_member.command import (
    RemoveStaticMemberCommand,
)
from src.modules.segmentation.domain.segment_definition import (
    SegmentDefinition,
    SegmentDefinitionCommandRepositoryProtocol,
    SegmentDefinitionNotFoundError,
    SegmentKindVO,
    SegmentStatusVO,
)
from src.modules.segmentation.domain.segment_static_member import (
    SegmentStaticMemberArchivedSegmentError,
    SegmentStaticMemberCommandRepositoryProtocol,
    SegmentStaticMemberNonStaticSegmentError,
)


class RemoveStaticMemberUseCaseProtocol(Protocol):
    """Use case port for removing static segment member."""

    async def __call__(self, command: RemoveStaticMemberCommand) -> bool:
        """Removes Contact from static segment idempotently."""
        ...


class RemoveStaticMemberUseCase:
    """Removes Contact from a static segment."""

    def __init__(
        self,
        *,
        segment_repository: SegmentDefinitionCommandRepositoryProtocol,
        member_repository: SegmentStaticMemberCommandRepositoryProtocol,
    ) -> None:
        self._segment_repository = segment_repository
        self._member_repository = member_repository

    async def __call__(self, command: RemoveStaticMemberCommand) -> bool:
        segment = await self._segment_repository.load(
            tenant_id=command.tenant_id,
            segment_id=command.segment_id,
        )
        if segment is None:
            raise SegmentDefinitionNotFoundError(str(command.segment_id))
        self._ensure_segment_can_change_members(segment)
        return await self._member_repository.remove(
            tenant_id=command.tenant_id,
            segment_id=command.segment_id,
            contact_id=command.contact_id,
        )

    @staticmethod
    def _ensure_segment_can_change_members(segment: SegmentDefinition) -> None:
        if segment.status == SegmentStatusVO.ARCHIVED:
            raise SegmentStaticMemberArchivedSegmentError(str(segment.segment_id))
        if segment.segment_kind != SegmentKindVO.STATIC:
            raise SegmentStaticMemberNonStaticSegmentError(str(segment.segment_id))


__all__ = [
    "RemoveStaticMemberUseCase",
    "RemoveStaticMemberUseCaseProtocol",
]
