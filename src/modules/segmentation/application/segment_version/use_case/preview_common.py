from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from src.modules.segmentation.application.segment_static_member.dto import (
    ContactSummaryDTO,
)
from src.modules.segmentation.application.segment_static_member.query import (
    ContactLookupProtocol,
)
from src.modules.segmentation.application.segment_version.dto import SegmentPreviewDTO
from src.modules.segmentation.application.segment_version.evaluation import (
    SegmentVersionEvaluationOptions,
    SegmentVersionEvaluationResult,
)
from src.modules.segmentation.domain.segment_version import InvalidSegmentVersionError
from src.modules.shared import EntityIdVO

_MIN_LIMIT = 1
_MAX_LIMIT = 100


def build_preview_options(
    *,
    limit: int,
    offset: int,
) -> SegmentVersionEvaluationOptions:
    """Validate preview pagination and build evaluator options."""
    if limit < _MIN_LIMIT or limit > _MAX_LIMIT:
        raise InvalidSegmentVersionError("Preview limit must be between 1 and 100.")
    if offset < 0:
        raise InvalidSegmentVersionError("Preview offset must be >= 0.")
    return SegmentVersionEvaluationOptions(limit=limit, offset=offset)


async def build_segment_preview_dto(
    *,
    tenant_id: EntityIdVO,
    evaluation: SegmentVersionEvaluationResult,
    limit: int,
    offset: int,
    include_contact_summary: bool,
    contact_lookup: ContactLookupProtocol,
) -> SegmentPreviewDTO:
    """Build preview DTO and preserve Contact id order for summaries."""
    contacts: tuple[ContactSummaryDTO, ...] = ()
    if include_contact_summary and evaluation.contact_ids:
        summaries = await contact_lookup.get_summaries(
            tenant_id=tenant_id,
            contact_ids=_contact_entity_ids(evaluation.contact_ids),
        )
        contacts = tuple(
            summaries[contact_id]
            for contact_id in evaluation.contact_ids
            if contact_id in summaries
        )
    return SegmentPreviewDTO(
        contact_ids=evaluation.contact_ids,
        contacts=contacts,
        limit=limit,
        offset=offset,
        count=evaluation.count,
        total=None,
        has_more=evaluation.count == limit,
    )


def _contact_entity_ids(contact_ids: Sequence[UUID]) -> tuple[EntityIdVO, ...]:
    return tuple(EntityIdVO.from_value(contact_id) for contact_id in contact_ids)


__all__ = [
    "build_preview_options",
    "build_segment_preview_dto",
]
