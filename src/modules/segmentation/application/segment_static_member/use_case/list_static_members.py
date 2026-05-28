from dataclasses import replace
from typing import Protocol

from src.modules.segmentation.application.segment_static_member.dto import (
    StaticMemberDTO,
)
from src.modules.segmentation.application.segment_static_member.query import (
    ContactLookupProtocol,
    ListStaticMembersQuery,
    SegmentStaticMemberQueryRepositoryProtocol,
)
from src.modules.shared import EntityIdVO


class ListStaticMembersUseCaseProtocol(Protocol):
    """Use case port for listing static segment members."""

    async def __call__(self, query: ListStaticMembersQuery) -> list[StaticMemberDTO]:
        """Lists static segment members."""
        ...


class ListStaticMembersUseCase:
    """Lists static Contact segment members."""

    def __init__(
        self,
        *,
        repository: SegmentStaticMemberQueryRepositoryProtocol,
        contact_lookup: ContactLookupProtocol,
    ) -> None:
        self._repository = repository
        self._contact_lookup = contact_lookup

    async def __call__(self, query: ListStaticMembersQuery) -> list[StaticMemberDTO]:
        items = await self._repository.list(
            tenant_id=query.tenant_id,
            segment_id=query.segment_id,
            limit=query.limit,
            offset=query.offset,
        )
        if not query.include_contact_summary or not items:
            return items

        summaries = await self._contact_lookup.get_summaries(
            tenant_id=query.tenant_id,
            contact_ids=[EntityIdVO.from_value(item.contact_id) for item in items],
        )
        return [replace(item, contact=summaries.get(item.contact_id)) for item in items]


__all__ = [
    "ListStaticMembersUseCase",
    "ListStaticMembersUseCaseProtocol",
]
