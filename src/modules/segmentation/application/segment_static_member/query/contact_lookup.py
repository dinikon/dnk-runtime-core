from collections.abc import Sequence
from typing import Protocol
from uuid import UUID

from src.modules.segmentation.application.segment_static_member.dto import (
    ContactSummaryDTO,
)
from src.modules.shared import EntityIdVO


class ContactLookupProtocol(Protocol):
    """Contact lookup port for Contact-only segmentation."""

    async def exists(
        self,
        *,
        tenant_id: EntityIdVO,
        contact_id: EntityIdVO,
    ) -> bool:
        """Returns whether Contact exists for tenant."""
        ...

    async def get_summary(
        self,
        *,
        tenant_id: EntityIdVO,
        contact_id: EntityIdVO,
    ) -> ContactSummaryDTO | None:
        """Returns Contact summary or None."""
        ...

    async def get_summaries(
        self,
        *,
        tenant_id: EntityIdVO,
        contact_ids: Sequence[EntityIdVO],
    ) -> dict[UUID, ContactSummaryDTO]:
        """Returns Contact summaries keyed by Contact UUID."""
        ...


__all__ = ["ContactLookupProtocol"]
