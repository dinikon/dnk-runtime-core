from typing import Protocol

from src.modules.segmentation.application.segment_static_member.dto import (
    StaticMemberDTO,
)
from src.modules.segmentation.domain.segment_definition import SegmentIdVO
from src.modules.shared import EntityIdVO


class SegmentStaticMemberQueryRepositoryProtocol(Protocol):
    """Query repository port for static segment members."""

    async def get(
        self,
        *,
        tenant_id: EntityIdVO,
        segment_id: SegmentIdVO,
        contact_id: EntityIdVO,
    ) -> StaticMemberDTO | None:
        """Returns one static member read model."""
        ...

    async def list(
        self,
        *,
        tenant_id: EntityIdVO,
        segment_id: SegmentIdVO,
        limit: int,
        offset: int,
    ) -> list[StaticMemberDTO]:
        """Returns a page of static member read models."""
        ...


__all__ = ["SegmentStaticMemberQueryRepositoryProtocol"]
