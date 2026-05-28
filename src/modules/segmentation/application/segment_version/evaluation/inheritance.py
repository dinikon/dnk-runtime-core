from __future__ import annotations

from collections.abc import Awaitable, Callable, Sequence
from uuid import UUID

from src.modules.segmentation.application.segment_static_member.query import (
    StaticContactAudienceQueryProtocol,
)
from src.modules.segmentation.application.segment_version.evaluation.error import (
    SegmentVersionActiveVersionNotFoundError,
    SegmentVersionEvaluationDepthExceededError,
    SegmentVersionEvaluationError,
    SegmentVersionEvaluationInheritanceCycleError,
)
from src.modules.segmentation.application.segment_version.evaluation.model import (
    SegmentVersionEvaluationOptions,
)
from src.modules.segmentation.domain.segment_definition import (
    SegmentDefinitionCommandRepositoryProtocol,
    SegmentIdVO,
    SegmentKindVO,
    SegmentStatusVO,
)
from src.modules.segmentation.domain.segment_version import (
    SegmentVersion,
    SegmentVersionCommandRepositoryProtocol,
)
from src.modules.shared import EntityIdVO

_MAX_INHERITANCE_DEPTH = 3

DynamicSegmentEvaluator = Callable[
    [SegmentIdVO, SegmentVersion, frozenset[UUID], int],
    Awaitable[tuple[UUID, ...]],
]


class SegmentVersionInheritanceEvaluator:
    """Evaluates inherited static or dynamic Contact segments."""

    def __init__(
        self,
        *,
        segment_repository: SegmentDefinitionCommandRepositoryProtocol,
        version_repository: SegmentVersionCommandRepositoryProtocol,
        static_audience_query: StaticContactAudienceQueryProtocol,
    ) -> None:
        self._segment_repository = segment_repository
        self._version_repository = version_repository
        self._static_audience_query = static_audience_query

    async def evaluate_inherited_segments(
        self,
        *,
        tenant_id: EntityIdVO,
        segment_ids: Sequence[SegmentIdVO],
        options: SegmentVersionEvaluationOptions,
        visited_segment_ids: frozenset[UUID],
        depth: int,
        evaluate_dynamic_segment: DynamicSegmentEvaluator,
    ) -> tuple[UUID, ...]:
        if depth >= _MAX_INHERITANCE_DEPTH:
            raise SegmentVersionEvaluationDepthExceededError(
                f"Segment inheritance depth must not exceed {_MAX_INHERITANCE_DEPTH}."
            )

        contact_ids: list[UUID] = []
        for segment_id in segment_ids:
            if segment_id.uuid in visited_segment_ids:
                raise SegmentVersionEvaluationInheritanceCycleError(
                    f"Segment inheritance cycle detected at {segment_id.uuid}."
                )

            segment = await self._segment_repository.load(
                tenant_id=tenant_id,
                segment_id=segment_id,
            )
            if segment is None:
                raise SegmentVersionEvaluationError(
                    f"Inherited segment {segment_id.uuid} not found."
                )
            if segment.status == SegmentStatusVO.ARCHIVED:
                raise SegmentVersionEvaluationError(
                    f"Inherited segment {segment_id.uuid} is archived."
                )

            if segment.segment_kind == SegmentKindVO.STATIC:
                contact_ids.extend(
                    await self._static_audience_query.list_contact_ids(
                        tenant_id=tenant_id,
                        segment_id=segment_id,
                        limit=options.max_items,
                        offset=0,
                    )
                )
                continue

            active_version = await self._version_repository.get_active(
                tenant_id=tenant_id,
                segment_id=segment_id,
            )
            if active_version is None:
                raise SegmentVersionActiveVersionNotFoundError(str(segment_id.uuid))
            contact_ids.extend(
                await evaluate_dynamic_segment(
                    segment_id,
                    active_version,
                    visited_segment_ids | frozenset({segment_id.uuid}),
                    depth + 1,
                )
            )
        return tuple(contact_ids)


__all__ = ["SegmentVersionInheritanceEvaluator"]
