from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import Any
from uuid import UUID

from src.modules.runtime_data.application.models import PageSpec, SortSpec
from src.modules.runtime_data.application.ports import (
    RuntimeCommandGateway,
    RuntimeQueryGateway,
)
from src.modules.schema_registry.runtime import (
    RuntimeObjectDescriptor,
    RuntimeObjectResolverProtocol,
)
from src.modules.segmentation.application.segment_definition.dto import (
    SegmentDefinitionDTO,
)
from src.modules.segmentation.application.segment_definition.query import (
    SegmentDefinitionQueryRepositoryProtocol,
)
from src.modules.segmentation.domain.segment_definition import (
    SegmentDefinition,
    SegmentDefinitionCommandRepositoryProtocol,
    SegmentDefinitionNotFoundError,
    SegmentIdVO,
    SegmentKindVO,
    SegmentStatusVO,
)
from src.modules.shared import EntityIdVO


class SegmentDefinitionRuntimeRepository(
    SegmentDefinitionCommandRepositoryProtocol,
    SegmentDefinitionQueryRepositoryProtocol,
):
    """Runtime repository for Contact segment definitions."""

    _OBJECT_NAME = "segment_definition"

    def __init__(
        self,
        *,
        runtime_object_resolver: RuntimeObjectResolverProtocol,
        runtime_command_gateway: RuntimeCommandGateway,
        runtime_query_gateway: RuntimeQueryGateway,
    ) -> None:
        self._runtime_object_resolver = runtime_object_resolver
        self._runtime_command_gateway = runtime_command_gateway
        self._runtime_query_gateway = runtime_query_gateway

    async def load(
        self,
        *,
        tenant_id: EntityIdVO,
        segment_id: SegmentIdVO,
    ) -> SegmentDefinition | None:
        descriptor = await self._resolve_descriptor(tenant_id)
        row = await self._runtime_query_gateway.get_by_id(
            descriptor=descriptor,
            object_id=segment_id.uuid,
        )
        if row is None:
            return None
        return self._row_to_entity(row)

    async def save(
        self,
        *,
        tenant_id: EntityIdVO,
        segment: SegmentDefinition,
    ) -> SegmentDefinition:
        descriptor = await self._resolve_descriptor(tenant_id)
        existing = await self._runtime_query_gateway.get_by_id(
            descriptor=descriptor,
            object_id=segment.segment_id.uuid,
        )
        payload = {
            "name": segment.name,
            "description": segment.description,
            "segment_kind": segment.segment_kind.value,
            "status": segment.status.value,
            "archived_at": segment.archived_at,
        }
        if existing is None:
            row = await self._runtime_command_gateway.insert(
                descriptor=descriptor,
                payload={
                    "id": segment.segment_id.uuid,
                    **payload,
                },
            )
        else:
            row = await self._runtime_command_gateway.update(
                descriptor=descriptor,
                object_id=segment.segment_id.uuid,
                patch=payload,
            )
            if row is None:
                raise SegmentDefinitionNotFoundError(str(segment.segment_id))
        return self._row_to_entity(row)

    async def get(
        self,
        *,
        tenant_id: EntityIdVO,
        segment_id: SegmentIdVO,
    ) -> SegmentDefinitionDTO | None:
        descriptor = await self._resolve_descriptor(tenant_id)
        row = await self._runtime_query_gateway.get_by_id(
            descriptor=descriptor,
            object_id=segment_id.uuid,
        )
        if row is None:
            return None
        return self._row_to_dto(row)

    async def list(
        self,
        *,
        tenant_id: EntityIdVO,
        limit: int,
        offset: int,
    ) -> list[SegmentDefinitionDTO]:
        descriptor = await self._resolve_descriptor(tenant_id)
        rows = await self._runtime_query_gateway.list(
            descriptor=descriptor,
            sorting=(
                SortSpec(field="created_at", direction="asc"),
                SortSpec(field="id", direction="asc"),
            ),
            page=PageSpec(limit=limit, offset=offset),
        )
        return [self._row_to_dto(row) for row in rows]

    async def _resolve_descriptor(
        self,
        tenant_id: EntityIdVO,
    ) -> RuntimeObjectDescriptor:
        return await self._runtime_object_resolver.resolve(
            tenant_id=tenant_id,
            object_name=self._OBJECT_NAME,
        )

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
    def _row_to_dto(row: Mapping[str, Any]) -> SegmentDefinitionDTO:
        return SegmentDefinitionDTO(
            id=SegmentDefinitionRuntimeRepository._as_uuid(row.get("id")),
            name=SegmentDefinitionRuntimeRepository._as_str(row.get("name")),
            segment_kind=SegmentDefinitionRuntimeRepository._as_str(
                row.get("segment_kind")
            ),
            status=SegmentDefinitionRuntimeRepository._as_str(row.get("status")),
            description=SegmentDefinitionRuntimeRepository._as_optional_str(
                row.get("description")
            ),
            archived_at=SegmentDefinitionRuntimeRepository._as_optional_datetime(
                row.get("archived_at")
            ),
            created_at=SegmentDefinitionRuntimeRepository._as_datetime(
                row.get("created_at")
            ),
            updated_at=SegmentDefinitionRuntimeRepository._as_datetime(
                row.get("updated_at")
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

    @staticmethod
    def _as_datetime(value: Any) -> datetime:
        if isinstance(value, datetime):
            return value
        raise TypeError("Runtime row must contain datetime value.")


__all__ = ["SegmentDefinitionRuntimeRepository"]
