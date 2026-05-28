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
from src.modules.runtime_data.application.query.typed_filter_builder import (
    RuntimeTypedFilterBuilder,
)
from src.modules.schema_registry.runtime import (
    RuntimeObjectDescriptor,
    RuntimeObjectResolverProtocol,
)
from src.modules.segmentation.application.segment_snapshot.dto import (
    SegmentSnapshotDTO,
)
from src.modules.segmentation.application.segment_snapshot.query import (
    SegmentSnapshotQueryRepositoryProtocol,
)
from src.modules.segmentation.domain.segment_definition import SegmentIdVO
from src.modules.segmentation.domain.segment_snapshot import (
    SegmentSnapshot,
    SegmentSnapshotCommandRepositoryProtocol,
    SegmentSnapshotIdVO,
    SegmentSnapshotNotFoundError,
    SegmentSnapshotStatusVO,
)
from src.modules.segmentation.domain.segment_version import SegmentVersionIdVO
from src.modules.shared import EntityIdVO


class SegmentSnapshotRuntimeRepository(
    SegmentSnapshotCommandRepositoryProtocol,
    SegmentSnapshotQueryRepositoryProtocol,
):
    """Runtime repository for Contact segment snapshots."""

    _OBJECT_NAME = "segment_snapshot"

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
        self._filter_builder = RuntimeTypedFilterBuilder()

    async def load(
        self,
        *,
        tenant_id: EntityIdVO,
        segment_snapshot_id: SegmentSnapshotIdVO,
    ) -> SegmentSnapshot | None:
        descriptor = await self._resolve_descriptor(tenant_id)
        row = await self._runtime_query_gateway.get_by_id(
            descriptor=descriptor,
            object_id=segment_snapshot_id.uuid,
        )
        if row is None:
            return None
        return self._row_to_entity(row)

    async def save(
        self,
        *,
        tenant_id: EntityIdVO,
        snapshot: SegmentSnapshot,
    ) -> SegmentSnapshot:
        descriptor = await self._resolve_descriptor(tenant_id)
        existing = await self._runtime_query_gateway.get_by_id(
            descriptor=descriptor,
            object_id=snapshot.segment_snapshot_id.uuid,
        )
        payload = {
            "segment_definition_id": snapshot.segment_id.uuid,
            "segment_version_id": snapshot.segment_version_id.uuid,
            "status": snapshot.status.value,
            "member_count": snapshot.member_count,
            "started_at": snapshot.started_at,
            "completed_at": snapshot.completed_at,
            "error_code": snapshot.error_code,
            "error_message": snapshot.error_message,
        }
        if existing is None:
            row = await self._runtime_command_gateway.insert(
                descriptor=descriptor,
                payload={
                    "id": snapshot.segment_snapshot_id.uuid,
                    **payload,
                },
            )
        else:
            row = await self._runtime_command_gateway.update(
                descriptor=descriptor,
                object_id=snapshot.segment_snapshot_id.uuid,
                patch=payload,
            )
            if row is None:
                raise SegmentSnapshotNotFoundError(
                    str(snapshot.segment_snapshot_id.uuid)
                )
        return self._row_to_entity(row)

    async def get(
        self,
        *,
        tenant_id: EntityIdVO,
        segment_snapshot_id: SegmentSnapshotIdVO,
    ) -> SegmentSnapshotDTO | None:
        descriptor = await self._resolve_descriptor(tenant_id)
        row = await self._runtime_query_gateway.get_by_id(
            descriptor=descriptor,
            object_id=segment_snapshot_id.uuid,
        )
        if row is None:
            return None
        return self._row_to_dto(row)

    async def list(
        self,
        *,
        tenant_id: EntityIdVO,
        segment_id: SegmentIdVO,
        limit: int,
        offset: int,
    ) -> list[SegmentSnapshotDTO]:
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
                SortSpec(field="created_at", direction="desc"),
                SortSpec(field="id", direction="desc"),
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
    def _row_to_entity(row: Mapping[str, Any]) -> SegmentSnapshot:
        return SegmentSnapshot.create(
            segment_snapshot_id=SegmentSnapshotIdVO.from_value(
                SegmentSnapshotRuntimeRepository._as_uuid(row.get("id"))
            ),
            segment_id=SegmentIdVO.from_value(
                SegmentSnapshotRuntimeRepository._as_uuid(
                    row.get("segment_definition_id")
                )
            ),
            segment_version_id=SegmentVersionIdVO.from_value(
                SegmentSnapshotRuntimeRepository._as_uuid(row.get("segment_version_id"))
            ),
            status=SegmentSnapshotStatusVO(
                SegmentSnapshotRuntimeRepository._as_str(row.get("status"))
            ),
            member_count=SegmentSnapshotRuntimeRepository._as_int(
                row.get("member_count")
            ),
            started_at=SegmentSnapshotRuntimeRepository._as_optional_datetime(
                row.get("started_at")
            ),
            completed_at=SegmentSnapshotRuntimeRepository._as_optional_datetime(
                row.get("completed_at")
            ),
            error_code=SegmentSnapshotRuntimeRepository._as_optional_str(
                row.get("error_code")
            ),
            error_message=SegmentSnapshotRuntimeRepository._as_optional_str(
                row.get("error_message")
            ),
        )

    @staticmethod
    def _row_to_dto(row: Mapping[str, Any]) -> SegmentSnapshotDTO:
        return SegmentSnapshotDTO(
            id=SegmentSnapshotRuntimeRepository._as_uuid(row.get("id")),
            segment_id=SegmentSnapshotRuntimeRepository._as_uuid(
                row.get("segment_definition_id")
            ),
            segment_version_id=SegmentSnapshotRuntimeRepository._as_uuid(
                row.get("segment_version_id")
            ),
            status=SegmentSnapshotRuntimeRepository._as_str(row.get("status")),
            member_count=SegmentSnapshotRuntimeRepository._as_int(
                row.get("member_count")
            ),
            started_at=SegmentSnapshotRuntimeRepository._as_optional_datetime(
                row.get("started_at")
            ),
            completed_at=SegmentSnapshotRuntimeRepository._as_optional_datetime(
                row.get("completed_at")
            ),
            error_code=SegmentSnapshotRuntimeRepository._as_optional_str(
                row.get("error_code")
            ),
            error_message=SegmentSnapshotRuntimeRepository._as_optional_str(
                row.get("error_message")
            ),
            created_at=SegmentSnapshotRuntimeRepository._as_datetime(
                row.get("created_at")
            ),
            updated_at=SegmentSnapshotRuntimeRepository._as_datetime(
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
    def _as_int(value: Any) -> int:
        if isinstance(value, int):
            return value
        raise TypeError("Runtime row must contain int value.")

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
    def _as_datetime(value: Any) -> datetime:
        if isinstance(value, datetime):
            return value
        raise TypeError("Runtime row must contain datetime value.")

    @staticmethod
    def _as_optional_datetime(value: Any) -> datetime | None:
        if value is None:
            return None
        if isinstance(value, datetime):
            return value
        raise TypeError("Runtime row must contain optional datetime value.")


__all__ = ["SegmentSnapshotRuntimeRepository"]
