from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol
from uuid import UUID

from src.modules.runtime_data.application.models import TypedFilterExpression
from src.modules.segmentation.application.segment_version.dsl import (
    SegmentVersionContactMapping,
)
from src.modules.shared import EntityIdVO


class ContactAudienceQueryProtocol(Protocol):
    """Runtime query port that maps object rows into Contact audience ids."""

    async def list_contact_ids(
        self,
        *,
        tenant_id: EntityIdVO,
        object_name: str,
        filters: Sequence[TypedFilterExpression],
        relation_path: Sequence[str],
        contact_mapping: SegmentVersionContactMapping,
        limit: int | None = None,
        offset: int = 0,
    ) -> tuple[UUID, ...]:
        """Return Contact ids matched by a dynamic segment rule."""
        ...


__all__ = ["ContactAudienceQueryProtocol"]
