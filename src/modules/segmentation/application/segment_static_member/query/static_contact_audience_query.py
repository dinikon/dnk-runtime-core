from __future__ import annotations

from typing import Protocol
from uuid import UUID

from src.modules.segmentation.domain.segment_definition import SegmentIdVO
from src.modules.shared import EntityIdVO


class StaticContactAudienceQueryProtocol(Protocol):
    """Query port for static Contact segment audience ids."""

    async def list_contact_ids(
        self,
        *,
        tenant_id: EntityIdVO,
        segment_id: SegmentIdVO,
        limit: int | None = None,
        offset: int = 0,
    ) -> tuple[UUID, ...]:
        """Return Contact ids for a static segment."""
        ...


__all__ = ["StaticContactAudienceQueryProtocol"]
