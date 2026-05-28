from dataclasses import replace
from typing import Protocol

from src.modules.segmentation.application.segment_snapshot.query import (
    SegmentSnapshotQueryRepositoryProtocol,
)
from src.modules.segmentation.application.segment_snapshot_member.dto import (
    SegmentSnapshotMemberDTO,
)
from src.modules.segmentation.application.segment_snapshot_member.query import (
    ListSegmentSnapshotMembersQuery,
    SegmentSnapshotMemberQueryRepositoryProtocol,
)
from src.modules.segmentation.application.segment_static_member.query import (
    ContactLookupProtocol,
)
from src.modules.segmentation.domain.segment_snapshot import (
    InvalidSegmentSnapshotError,
    SegmentSnapshotNotFoundError,
)
from src.modules.shared import EntityIdVO


class ListSegmentSnapshotMembersUseCaseProtocol(Protocol):
    """Use case port for listing segment snapshot members."""

    async def __call__(
        self,
        query: ListSegmentSnapshotMembersQuery,
    ) -> list[SegmentSnapshotMemberDTO]:
        """Lists segment snapshot members."""
        ...


class ListSegmentSnapshotMembersUseCase:
    """Lists frozen Contact audience snapshot members."""

    def __init__(
        self,
        *,
        snapshot_repository: SegmentSnapshotQueryRepositoryProtocol,
        member_repository: SegmentSnapshotMemberQueryRepositoryProtocol,
        contact_lookup: ContactLookupProtocol,
    ) -> None:
        self._snapshot_repository = snapshot_repository
        self._member_repository = member_repository
        self._contact_lookup = contact_lookup

    async def __call__(
        self,
        query: ListSegmentSnapshotMembersQuery,
    ) -> list[SegmentSnapshotMemberDTO]:
        if query.limit < 1 or query.limit > 500:
            raise InvalidSegmentSnapshotError(
                "Snapshot member list limit must be 1..500."
            )
        if query.offset < 0:
            raise InvalidSegmentSnapshotError(
                "Snapshot member list offset must be >= 0."
            )
        snapshot = await self._snapshot_repository.get(
            tenant_id=query.tenant_id,
            segment_snapshot_id=query.segment_snapshot_id,
        )
        if snapshot is None:
            raise SegmentSnapshotNotFoundError(str(query.segment_snapshot_id.uuid))

        items = await self._member_repository.list(
            tenant_id=query.tenant_id,
            segment_snapshot_id=query.segment_snapshot_id,
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
    "ListSegmentSnapshotMembersUseCase",
    "ListSegmentSnapshotMembersUseCaseProtocol",
]
