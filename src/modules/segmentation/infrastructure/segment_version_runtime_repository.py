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
from src.modules.segmentation.application.segment_version.dto import SegmentVersionDTO
from src.modules.segmentation.application.segment_version.query import (
    SegmentVersionQueryRepositoryProtocol,
)
from src.modules.segmentation.domain.segment_definition import SegmentIdVO
from src.modules.segmentation.domain.segment_version import (
    SegmentVersion,
    SegmentVersionCommandRepositoryProtocol,
    SegmentVersionIdVO,
    SegmentVersionNotFoundError,
    SegmentVersionStatusVO,
)
from src.modules.shared import EntityIdVO


class SegmentVersionRuntimeRepository(
    SegmentVersionCommandRepositoryProtocol,
    SegmentVersionQueryRepositoryProtocol,
):
    """Runtime repository for Contact segment versions."""

    _OBJECT_NAME = "segment_version"

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
        segment_version_id: SegmentVersionIdVO,
    ) -> SegmentVersion | None:
        descriptor = await self._resolve_descriptor(tenant_id)
        row = await self._runtime_query_gateway.get_by_id(
            descriptor=descriptor,
            object_id=segment_version_id.uuid,
        )
        if row is None:
            return None
        return self._row_to_entity(row)

    async def get_active(
        self,
        *,
        tenant_id: EntityIdVO,
        segment_id: SegmentIdVO,
    ) -> SegmentVersion | None:
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
                self._filter_builder.condition(
                    descriptor=descriptor,
                    field="status",
                    op="eq",
                    value=SegmentVersionStatusVO.ACTIVE.value,
                ),
            ),
            sorting=(SortSpec(field="version_number", direction="desc"),),
            page=PageSpec(limit=1, offset=0),
        )
        return None if not rows else self._row_to_entity(rows[0])

    async def get_next_version_number(
        self,
        *,
        tenant_id: EntityIdVO,
        segment_id: SegmentIdVO,
    ) -> int:
        descriptor = await self._resolve_descriptor(tenant_id)
        await self._runtime_command_gateway.acquire_advisory_xact_lock(
            f"segmentation_segment_version:{tenant_id.uuid}:{segment_id.uuid}"
        )
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
            sorting=(SortSpec(field="version_number", direction="desc"),),
            page=PageSpec(limit=1, offset=0),
        )
        if not rows:
            return 1
        return self._as_int(rows[0].get("version_number")) + 1

    async def save(
        self,
        *,
        tenant_id: EntityIdVO,
        version: SegmentVersion,
    ) -> SegmentVersion:
        descriptor = await self._resolve_descriptor(tenant_id)
        existing = await self._runtime_query_gateway.get_by_id(
            descriptor=descriptor,
            object_id=version.segment_version_id.uuid,
        )
        payload = {
            "segment_definition_id": version.segment_id.uuid,
            "version_number": version.version_number,
            "status": version.status.value,
            "config": dict(version.config),
            "config_checksum": version.config_checksum,
            "activated_at": version.activated_at,
            "archived_at": version.archived_at,
        }
        if existing is None:
            row = await self._runtime_command_gateway.insert(
                descriptor=descriptor,
                payload={
                    "id": version.segment_version_id.uuid,
                    **payload,
                },
            )
        else:
            row = await self._runtime_command_gateway.update(
                descriptor=descriptor,
                object_id=version.segment_version_id.uuid,
                patch=payload,
            )
            if row is None:
                raise SegmentVersionNotFoundError(str(version.segment_version_id))
        return self._row_to_entity(row)

    async def archive_active_versions(
        self,
        *,
        tenant_id: EntityIdVO,
        segment_id: SegmentIdVO,
        now: datetime,
    ) -> None:
        descriptor = await self._resolve_descriptor(tenant_id)
        await self._runtime_command_gateway.update_where(
            descriptor=descriptor,
            filters=(
                self._filter_builder.condition(
                    descriptor=descriptor,
                    field="segment_definition_id",
                    op="eq",
                    value=segment_id.uuid,
                ),
                self._filter_builder.condition(
                    descriptor=descriptor,
                    field="status",
                    op="eq",
                    value=SegmentVersionStatusVO.ACTIVE.value,
                ),
            ),
            patch={
                "status": SegmentVersionStatusVO.ARCHIVED.value,
                "archived_at": now,
            },
        )

    async def get(
        self,
        *,
        tenant_id: EntityIdVO,
        segment_id: SegmentIdVO,
        segment_version_id: SegmentVersionIdVO,
    ) -> SegmentVersionDTO | None:
        descriptor = await self._resolve_descriptor(tenant_id)
        row = await self._runtime_query_gateway.get_by_id(
            descriptor=descriptor,
            object_id=segment_version_id.uuid,
        )
        if row is None:
            return None
        dto = self._row_to_dto(row)
        if dto.segment_id != segment_id.uuid:
            return None
        return dto

    async def list(
        self,
        *,
        tenant_id: EntityIdVO,
        segment_id: SegmentIdVO,
        limit: int,
        offset: int,
    ) -> list[SegmentVersionDTO]:
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
                SortSpec(field="version_number", direction="asc"),
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
    def _row_to_entity(row: Mapping[str, Any]) -> SegmentVersion:
        return SegmentVersion(
            segment_version_id=SegmentVersionIdVO.from_value(
                SegmentVersionRuntimeRepository._as_uuid(row.get("id"))
            ),
            segment_id=SegmentIdVO.from_value(
                SegmentVersionRuntimeRepository._as_uuid(
                    row.get("segment_definition_id")
                )
            ),
            version_number=SegmentVersionRuntimeRepository._as_int(
                row.get("version_number")
            ),
            status=SegmentVersionStatusVO(
                SegmentVersionRuntimeRepository._as_str(row.get("status"))
            ),
            config=SegmentVersionRuntimeRepository._as_dict(row.get("config")),
            config_checksum=SegmentVersionRuntimeRepository._as_str(
                row.get("config_checksum")
            ),
            activated_at=SegmentVersionRuntimeRepository._as_optional_datetime(
                row.get("activated_at")
            ),
            archived_at=SegmentVersionRuntimeRepository._as_optional_datetime(
                row.get("archived_at")
            ),
        )

    @staticmethod
    def _row_to_dto(row: Mapping[str, Any]) -> SegmentVersionDTO:
        return SegmentVersionDTO(
            id=SegmentVersionRuntimeRepository._as_uuid(row.get("id")),
            segment_id=SegmentVersionRuntimeRepository._as_uuid(
                row.get("segment_definition_id")
            ),
            version_number=SegmentVersionRuntimeRepository._as_int(
                row.get("version_number")
            ),
            status=SegmentVersionRuntimeRepository._as_str(row.get("status")),
            config=SegmentVersionRuntimeRepository._as_dict(row.get("config")),
            config_checksum=SegmentVersionRuntimeRepository._as_str(
                row.get("config_checksum")
            ),
            activated_at=SegmentVersionRuntimeRepository._as_optional_datetime(
                row.get("activated_at")
            ),
            archived_at=SegmentVersionRuntimeRepository._as_optional_datetime(
                row.get("archived_at")
            ),
            created_at=SegmentVersionRuntimeRepository._as_datetime(
                row.get("created_at")
            ),
            updated_at=SegmentVersionRuntimeRepository._as_datetime(
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
    def _as_dict(value: Any) -> dict[str, Any]:
        if isinstance(value, Mapping):
            return dict(value)
        raise TypeError("Runtime row must contain dict value.")

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


__all__ = ["SegmentVersionRuntimeRepository"]
