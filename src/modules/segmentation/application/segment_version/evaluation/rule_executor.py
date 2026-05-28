from __future__ import annotations

from uuid import UUID

from src.modules.runtime_data.domain.error import RuntimeDataFilterError
from src.modules.segmentation.application.segment_version.dsl import (
    SegmentVersionDslRule,
)
from src.modules.segmentation.application.segment_version.dsl.filter_to_runtime import (
    build_runtime_filter_specs,
)
from src.modules.segmentation.application.segment_version.evaluation.error import (
    SegmentVersionEvaluationFilterError,
)
from src.modules.segmentation.application.segment_version.query import (
    ContactAudienceQueryProtocol,
    RuntimeObjectMetadataProtocol,
)
from src.modules.shared import EntityIdVO


class SegmentVersionRuleExecutor:
    """Executes validated segment version DSL rules against runtime_data."""

    def __init__(
        self,
        *,
        metadata: RuntimeObjectMetadataProtocol,
        contact_audience_query: ContactAudienceQueryProtocol,
    ) -> None:
        self._metadata = metadata
        self._contact_audience_query = contact_audience_query

    async def execute_rule(
        self,
        *,
        tenant_id: EntityIdVO,
        rule: SegmentVersionDslRule,
        limit: int | None = None,
        offset: int = 0,
    ) -> tuple[UUID, ...]:
        descriptor = await self._metadata.resolve_object(
            tenant_id=tenant_id,
            object_name=rule.object,
        )
        try:
            filters = build_runtime_filter_specs(
                descriptor=descriptor,
                filter_config=rule.filter,
            )
        except RuntimeDataFilterError as exc:
            raise SegmentVersionEvaluationFilterError(str(exc)) from exc

        return await self._contact_audience_query.list_contact_ids(
            tenant_id=tenant_id,
            object_name=rule.object,
            filters=filters,
            relation_path=rule.relation_path,
            contact_mapping=rule.contact_mapping,
            limit=limit,
            offset=offset,
        )


__all__ = ["SegmentVersionRuleExecutor"]
