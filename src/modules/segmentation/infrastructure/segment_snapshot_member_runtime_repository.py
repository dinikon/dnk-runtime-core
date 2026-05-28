from __future__ import annotations

from collections.abc import Mapping, Sequence
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
from src.modules.segmentation.application.segment_snapshot_member.dto import (
    SegmentSnapshotMemberDTO,
)
from src.modules.segmentation.application.segment_snapshot_member.query import (
    SegmentSnapshotMemberQueryRepositoryProtocol,
)
from src.modules.segmentation.domain.segment_snapshot import SegmentSnapshotIdVO
from src.modules.segmentation.domain.segment_snapshot_member import (
    InvalidSegmentSnapshotMemberError,
    SegmentSnapshotMemberCommandRepositoryProtocol,
)
from src.modules.shared import EntityIdVO


class SegmentSnapshotMemberRuntimeRepository(
    SegmentSnapshotMemberCommandRepositoryProtocol,
    SegmentSnapshotMemberQueryRepositoryProtocol,
):
    """Runtime repository for frozen Contact segment snapshot members."""

    _OBJECT_NAME = "segment_snapshot_member"

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

    async def add_members(
        self,
        *,
        tenant_id: EntityIdVO,
        segment_snapshot_id: SegmentSnapshotIdVO,
        contact_ids: Sequence[EntityIdVO],
        start_position: int = 0,
    ) -> int:
        if start_position < 0:
            raise InvalidSegmentSnapshotMemberError(
                "Segment snapshot member start position must be >= 0."
            )
        descriptor = await self._resolve_descriptor(tenant_id)
        unique_contact_ids = self._dedupe_contact_ids(contact_ids)
        for index, contact_id in enumerate(unique_contact_ids):
            try:
                await self._runtime_command_gateway.insert(
                    descriptor=descriptor,
                    payload={
                        "segment_snapshot_id": segment_snapshot_id.uuid,
                        "contact_id": contact_id.uuid,
                        "position": start_position + index,
                    },
                )
            except RuntimeDataPersistenceError:
                existing = await self._find_member_row(
                    descriptor=descriptor,
                    segment_snapshot_id=segment_snapshot_id,
                    contact_id=contact_id,
                )
                if existing is None:
                    raise
        return len(unique_contact_ids)

    async def delete_for_failed_snapshot(
        self,
        *,
        tenant_id: EntityIdVO,
        segment_snapshot_id: SegmentSnapshotIdVO,
    ) -> None:
        descriptor = await self._resolve_descriptor(tenant_id)
        rows = await self._runtime_query_gateway.list(
            descriptor=descriptor,
            filters=(
                self._filter_builder.condition(
                    descriptor=descriptor,
                    field="segment_snapshot_id",
                    op="eq",
                    value=segment_snapshot_id.uuid,
                ),
            ),
        )
        for row in rows:
            await self._runtime_command_gateway.delete(
                descriptor=descriptor,
                object_id=self._as_uuid(row.get("id")),
            )

    async def list(
        self,
        *,
        tenant_id: EntityIdVO,
        segment_snapshot_id: SegmentSnapshotIdVO,
        limit: int,
        offset: int,
    ) -> list[SegmentSnapshotMemberDTO]:
        descriptor = await self._resolve_descriptor(tenant_id)
        rows = await self._runtime_query_gateway.list(
            descriptor=descriptor,
            filters=(
                self._filter_builder.condition(
                    descriptor=descriptor,
                    field="segment_snapshot_id",
                    op="eq",
                    value=segment_snapshot_id.uuid,
                ),
            ),
            sorting=(
                SortSpec(field="position", direction="asc"),
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
        segment_snapshot_id: SegmentSnapshotIdVO,
        contact_id: EntityIdVO,
    ) -> Mapping[str, Any] | None:
        rows = await self._runtime_query_gateway.list(
            descriptor=descriptor,
            filters=(
                self._filter_builder.condition(
                    descriptor=descriptor,
                    field="segment_snapshot_id",
                    op="eq",
                    value=segment_snapshot_id.uuid,
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
    def _dedupe_contact_ids(
        contact_ids: Sequence[EntityIdVO],
    ) -> tuple[EntityIdVO, ...]:
        seen: set[UUID] = set()
        result: list[EntityIdVO] = []
        for contact_id in contact_ids:
            if contact_id.uuid in seen:
                continue
            seen.add(contact_id.uuid)
            result.append(contact_id)
        return tuple(result)

    @staticmethod
    def _row_to_dto(row: Mapping[str, Any]) -> SegmentSnapshotMemberDTO:
        return SegmentSnapshotMemberDTO(
            id=SegmentSnapshotMemberRuntimeRepository._as_uuid(row.get("id")),
            segment_snapshot_id=SegmentSnapshotMemberRuntimeRepository._as_uuid(
                row.get("segment_snapshot_id")
            ),
            contact_id=SegmentSnapshotMemberRuntimeRepository._as_uuid(
                row.get("contact_id")
            ),
            position=SegmentSnapshotMemberRuntimeRepository._as_optional_int(
                row.get("position")
            ),
            created_at=SegmentSnapshotMemberRuntimeRepository._as_datetime(
                row.get("created_at")
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
    def _as_optional_int(value: Any) -> int | None:
        if value is None:
            return None
        if isinstance(value, int):
            return value
        raise TypeError("Runtime row must contain optional int value.")


__all__ = ["SegmentSnapshotMemberRuntimeRepository"]
