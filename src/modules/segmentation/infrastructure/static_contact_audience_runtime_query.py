from __future__ import annotations

from collections.abc import Mapping
from typing import Any
from uuid import UUID

from src.modules.runtime_data.application.models import PageSpec, SortSpec
from src.modules.runtime_data.application.ports import RuntimeQueryGateway
from src.modules.runtime_data.application.query.typed_filter_builder import (
    RuntimeTypedFilterBuilder,
)
from src.modules.schema_registry.runtime import (
    RuntimeObjectDescriptor,
    RuntimeObjectResolverProtocol,
)
from src.modules.segmentation.application.segment_static_member.query import (
    StaticContactAudienceQueryProtocol,
)
from src.modules.segmentation.application.segment_version.evaluation import (
    SegmentVersionEvaluationInvalidMappingError,
)
from src.modules.segmentation.domain.segment_definition import SegmentIdVO
from src.modules.shared import EntityIdVO


class StaticContactAudienceRuntimeQuery(StaticContactAudienceQueryProtocol):
    """Runtime query adapter for static Contact segment member ids."""

    _OBJECT_NAME = "segment_static_member"

    def __init__(
        self,
        *,
        runtime_object_resolver: RuntimeObjectResolverProtocol,
        runtime_query_gateway: RuntimeQueryGateway,
    ) -> None:
        self._runtime_object_resolver = runtime_object_resolver
        self._runtime_query_gateway = runtime_query_gateway
        self._filter_builder = RuntimeTypedFilterBuilder()

    async def list_contact_ids(
        self,
        *,
        tenant_id: EntityIdVO,
        segment_id: SegmentIdVO,
        limit: int | None = None,
        offset: int = 0,
    ) -> tuple[UUID, ...]:
        descriptor = await self._resolve_descriptor(tenant_id)
        rows = await self._runtime_query_gateway.list(
            descriptor=descriptor,
            filters=(
                self._filter_builder.condition(
                    descriptor=descriptor,
                    field="segment_definition_id",
                    op="eq",
                    value=segment_id.uuid,
                ),
            ),
            sorting=(
                SortSpec(field="created_at", direction="asc"),
                SortSpec(field="id", direction="asc"),
            ),
            page=None if limit is None else PageSpec(limit=limit, offset=offset),
        )
        return tuple(self._row_to_contact_id(row) for row in rows)

    async def _resolve_descriptor(
        self,
        tenant_id: EntityIdVO,
    ) -> RuntimeObjectDescriptor:
        return await self._runtime_object_resolver.resolve(
            tenant_id=tenant_id,
            object_name=self._OBJECT_NAME,
        )

    @staticmethod
    def _row_to_contact_id(row: Mapping[str, Any]) -> UUID:
        if "contact_id" not in row or row.get("contact_id") is None:
            raise SegmentVersionEvaluationInvalidMappingError(
                "Static segment member row does not contain contact_id."
            )
        try:
            return StaticContactAudienceRuntimeQuery._as_uuid(row.get("contact_id"))
        except (TypeError, ValueError) as exc:
            raise SegmentVersionEvaluationInvalidMappingError(
                "Static segment member contact_id is not a valid UUID."
            ) from exc

    @staticmethod
    def _as_uuid(value: Any) -> UUID:
        if isinstance(value, UUID):
            return value
        if isinstance(value, EntityIdVO):
            return value.uuid
        if isinstance(value, str):
            return UUID(value)
        raise TypeError("Runtime row must contain UUID value.")


__all__ = ["StaticContactAudienceRuntimeQuery"]
