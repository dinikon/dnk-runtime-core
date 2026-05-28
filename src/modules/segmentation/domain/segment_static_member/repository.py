from typing import Protocol

from src.modules.segmentation.domain.segment_definition import SegmentIdVO
from src.modules.segmentation.domain.segment_static_member.entity import (
    SegmentStaticMember,
)
from src.modules.shared import EntityIdVO


class SegmentStaticMemberCommandRepositoryProtocol(Protocol):
    """Command repository port for static segment members."""

    async def exists(
        self,
        *,
        tenant_id: EntityIdVO,
        segment_id: SegmentIdVO,
        contact_id: EntityIdVO,
    ) -> bool:
        """Checks whether Contact is already a static member."""
        ...

    async def add(
        self,
        *,
        tenant_id: EntityIdVO,
        member: SegmentStaticMember,
    ) -> SegmentStaticMember:
        """Adds a static member idempotently."""
        ...

    async def remove(
        self,
        *,
        tenant_id: EntityIdVO,
        segment_id: SegmentIdVO,
        contact_id: EntityIdVO,
    ) -> bool:
        """Removes a static member idempotently."""
        ...


__all__ = ["SegmentStaticMemberCommandRepositoryProtocol"]
