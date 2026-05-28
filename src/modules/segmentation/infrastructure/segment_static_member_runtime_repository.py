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
from src.modules.runtime_data.domain.error import RuntimeDataPersistenceError
from src.modules.schema_registry.runtime import (
    RuntimeObjectDescriptor,
    RuntimeObjectResolverProtocol,
)
from src.modules.segmentation.application.segment_static_member.dto import (
    StaticMemberDTO,
)
from src.modules.segmentation.application.segment_static_member.query import (
    SegmentStaticMemberQueryRepositoryProtocol,
)
from src.modules.segmentation.domain.segment_definition import SegmentIdVO
from src.modules.segmentation.domain.segment_static_member import (
    SegmentStaticMember,
    SegmentStaticMemberCommandRepositoryProtocol,
    SegmentStaticMemberIdVO,
    SegmentStaticMemberSourceTypeVO,
)
from src.modules.shared import EntityIdVO


class SegmentStaticMemberRuntimeRepository(
    SegmentStaticMemberCommandRepositoryProtocol,
    SegmentStaticMemberQueryRepositoryProtocol,
):
    """Runtime repository for static Contact segment members."""

    _OBJECT_NAME = "segment_static_member"

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

    async def exists(
        self,
        *,
        tenant_id: EntityIdVO,
        segment_id: SegmentIdVO,
        contact_id: EntityIdVO,
    ) -> bool:
        descriptor = await self._resolve_descriptor(tenant_id)
        row = await self._find_member_row(
            descriptor=descriptor,
            segment_id=segment_id,
            contact_id=contact_id,
        )
        return row is not None

    async def add(
        self,
        *,
        tenant_id: EntityIdVO,
        member: SegmentStaticMember,
    ) -> SegmentStaticMember:
        descriptor = await self._resolve_descriptor(tenant_id)
        await self._runtime_command_gateway.acquire_advisory_xact_lock(
            self._lock_key(
                tenant_id=tenant_id,
                segment_id=member.segment_id,
                contact_id=member.contact_id,
            )
        )
        existing = await self._find_member_row(
            descriptor=descriptor,
            segment_id=member.segment_id,
            contact_id=member.contact_id,
        )
        if existing is not None:
            return self._row_to_entity(existing)

        try:
            row = await self._runtime_command_gateway.insert(
                descriptor=descriptor,
                payload={
                    "id": member.segment_static_member_id.uuid,
                    "segment_definition_id": member.segment_id.uuid,
                    "contact_id": member.contact_id.uuid,
                    "source_type": member.source_type.value,
                    "metadata": (
                        None if member.metadata is None else dict(member.metadata)
                    ),
                },
            )
        except RuntimeDataPersistenceError:
            existing = await self._find_member_row(
                descriptor=descriptor,
                segment_id=member.segment_id,
                contact_id=member.contact_id,
            )
            if existing is not None:
                return self._row_to_entity(existing)
            raise
        return self._row_to_entity(row)

    async def remove(
        self,
        *,
        tenant_id: EntityIdVO,
        segment_id: SegmentIdVO,
        contact_id: EntityIdVO,
    ) -> bool:
        descriptor = await self._resolve_descriptor(tenant_id)
        await self._runtime_command_gateway.acquire_advisory_xact_lock(
            self._lock_key(
                tenant_id=tenant_id,
                segment_id=segment_id,
                contact_id=contact_id,
            )
        )
        existing = await self._find_member_row(
            descriptor=descriptor,
            segment_id=segment_id,
            contact_id=contact_id,
        )
        if existing is None:
            return False
        return await self._runtime_command_gateway.delete(
            descriptor=descriptor,
            object_id=self._as_uuid(existing.get("id")),
        )

    async def get(
        self,
        *,
        tenant_id: EntityIdVO,
        segment_id: SegmentIdVO,
        contact_id: EntityIdVO,
    ) -> StaticMemberDTO | None:
        descriptor = await self._resolve_descriptor(tenant_id)
        row = await self._find_member_row(
            descriptor=descriptor,
            segment_id=segment_id,
            contact_id=contact_id,
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
    ) -> list[StaticMemberDTO]:
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

    async def _find_member_row(
        self,
        *,
        descriptor: RuntimeObjectDescriptor,
        segment_id: SegmentIdVO,
        contact_id: EntityIdVO,
    ) -> Mapping[str, Any] | None:
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
                    field="contact_id",
                    op="eq",
                    value=contact_id.uuid,
                ),
            ),
            page=PageSpec(limit=1, offset=0),
        )
        return rows[0] if rows else None

    @staticmethod
    def _lock_key(
        *,
        tenant_id: EntityIdVO,
        segment_id: SegmentIdVO,
        contact_id: EntityIdVO,
    ) -> str:
        return (
            "segmentation_static_member:"
            f"{tenant_id.uuid}:{segment_id.uuid}:{contact_id.uuid}"
        )

    @staticmethod
    def _row_to_entity(row: Mapping[str, Any]) -> SegmentStaticMember:
        return SegmentStaticMember(
            segment_static_member_id=SegmentStaticMemberIdVO.from_value(
                SegmentStaticMemberRuntimeRepository._as_uuid(row.get("id"))
            ),
            segment_id=SegmentIdVO.from_value(
                SegmentStaticMemberRuntimeRepository._as_uuid(
                    row.get("segment_definition_id")
                )
            ),
            contact_id=EntityIdVO.from_value(
                SegmentStaticMemberRuntimeRepository._as_uuid(row.get("contact_id"))
            ),
            source_type=SegmentStaticMemberSourceTypeVO(
                SegmentStaticMemberRuntimeRepository._as_str(row.get("source_type"))
            ),
            metadata=SegmentStaticMemberRuntimeRepository._as_optional_dict(
                row.get("metadata")
            ),
        )

    @staticmethod
    def _row_to_dto(row: Mapping[str, Any]) -> StaticMemberDTO:
        return StaticMemberDTO(
            id=SegmentStaticMemberRuntimeRepository._as_uuid(row.get("id")),
            segment_id=SegmentStaticMemberRuntimeRepository._as_uuid(
                row.get("segment_definition_id")
            ),
            contact_id=SegmentStaticMemberRuntimeRepository._as_uuid(
                row.get("contact_id")
            ),
            source_type=SegmentStaticMemberRuntimeRepository._as_str(
                row.get("source_type")
            ),
            metadata=SegmentStaticMemberRuntimeRepository._as_optional_dict(
                row.get("metadata")
            ),
            created_at=SegmentStaticMemberRuntimeRepository._as_datetime(
                row.get("created_at")
            ),
            updated_at=SegmentStaticMemberRuntimeRepository._as_datetime(
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
    def _as_datetime(value: Any) -> datetime:
        if isinstance(value, datetime):
            return value
        raise TypeError("Runtime row must contain datetime value.")

    @staticmethod
    def _as_str(value: Any) -> str:
        if isinstance(value, str):
            return value
        raise TypeError("Runtime row must contain string value.")

    @staticmethod
    def _as_optional_dict(value: Any) -> dict[str, Any] | None:
        if value is None:
            return None
        if isinstance(value, Mapping):
            return dict(value)
        raise TypeError("Runtime row must contain optional dict value.")


__all__ = ["SegmentStaticMemberRuntimeRepository"]
