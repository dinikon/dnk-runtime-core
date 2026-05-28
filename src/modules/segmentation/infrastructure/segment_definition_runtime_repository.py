from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import Any
from uuid import UUID

from src.modules.runtime_data.application.ports import RuntimeQueryGateway
from src.modules.schema_registry.runtime import RuntimeObjectResolverProtocol
from src.modules.segmentation.domain.segment_definition import (
    SegmentDefinition,
    SegmentDefinitionCommandRepositoryProtocol,
    SegmentIdVO,
    SegmentKindVO,
    SegmentStatusVO,
)
from src.modules.shared import EntityIdVO


class SegmentDefinitionRuntimeRepository(
    SegmentDefinitionCommandRepositoryProtocol,
):
    """Minimal segment definition repository needed by static members."""

    _OBJECT_NAME = "segment_definition"

    def __init__(
        self,
        *,
        runtime_object_resolver: RuntimeObjectResolverProtocol,
        runtime_query_gateway: RuntimeQueryGateway,
    ) -> None:
        self._runtime_object_resolver = runtime_object_resolver
        self._runtime_query_gateway = runtime_query_gateway

    async def load(
        self,
        *,
        tenant_id: EntityIdVO,
        segment_id: SegmentIdVO,
    ) -> SegmentDefinition | None:
        descriptor = await self._runtime_object_resolver.resolve(
            tenant_id=tenant_id,
            object_name=self._OBJECT_NAME,
        )
        row = await self._runtime_query_gateway.get_by_id(
            descriptor=descriptor,
            object_id=segment_id.uuid,
        )
        if row is None:
            return None
        return self._row_to_entity(row)

    @staticmethod
    def _row_to_entity(row: Mapping[str, Any]) -> SegmentDefinition:
        return SegmentDefinition(
            segment_id=SegmentIdVO.from_value(
                SegmentDefinitionRuntimeRepository._as_uuid(row.get("id"))
            ),
            name=SegmentDefinitionRuntimeRepository._as_str(row.get("name")),
            segment_kind=SegmentKindVO(
                SegmentDefinitionRuntimeRepository._as_str(row.get("segment_kind"))
            ),
            status=SegmentStatusVO(
                SegmentDefinitionRuntimeRepository._as_str(row.get("status"))
            ),
            description=SegmentDefinitionRuntimeRepository._as_optional_str(
                row.get("description")
            ),
            archived_at=SegmentDefinitionRuntimeRepository._as_optional_datetime(
                row.get("archived_at")
            ),
        )

    @staticmethod
    def _as_uuid(value: Any) -> UUID:
        if isinstance(value, UUID):
            return value
        if isinstance(value, str):
            return UUID(value)
        raise TypeError("Runtime row must contain UUID value.")

    @staticmethod
    def _as_str(value: Any) -> str:
        if isinstance(value, str):
            return value
        raise TypeError("Runtime row must contain string value.")

    @staticmethod
    def _as_optional_str(value: Any) -> str | None:
        if value is None:
            return None
        if isinstance(value, str):
            return value
        raise TypeError("Runtime row must contain optional string value.")

    @staticmethod
    def _as_optional_datetime(value: Any) -> datetime | None:
        if value is None:
            return None
        if isinstance(value, datetime):
            return value
        raise TypeError("Runtime row must contain optional datetime value.")


__all__ = ["SegmentDefinitionRuntimeRepository"]
