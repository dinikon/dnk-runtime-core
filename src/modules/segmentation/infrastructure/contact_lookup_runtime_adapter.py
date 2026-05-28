from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any
from uuid import UUID

from src.modules.runtime_data.application.ports import RuntimeQueryGateway
from src.modules.runtime_data.application.query.typed_filter_builder import (
    RuntimeTypedFilterBuilder,
)
from src.modules.schema_registry.runtime import RuntimeObjectResolverProtocol
from src.modules.segmentation.application.segment_static_member.dto import (
    ContactSummaryDTO,
)
from src.modules.segmentation.application.segment_static_member.query import (
    ContactLookupProtocol,
)
from src.modules.shared import EntityIdVO


class RuntimeContactLookupAdapter(ContactLookupProtocol):
    """Contact lookup adapter over runtime_data without CRM domain imports."""

    _OBJECT_NAME = "contact"

    def __init__(
        self,
        *,
        runtime_object_resolver: RuntimeObjectResolverProtocol,
        runtime_query_gateway: RuntimeQueryGateway,
    ) -> None:
        self._runtime_object_resolver = runtime_object_resolver
        self._runtime_query_gateway = runtime_query_gateway
        self._filter_builder = RuntimeTypedFilterBuilder()

    async def exists(
        self,
        *,
        tenant_id: EntityIdVO,
        contact_id: EntityIdVO,
    ) -> bool:
        descriptor = await self._resolve_descriptor(tenant_id)
        row = await self._runtime_query_gateway.get_by_id(
            descriptor=descriptor,
            object_id=contact_id.uuid,
        )
        return row is not None

    async def get_summary(
        self,
        *,
        tenant_id: EntityIdVO,
        contact_id: EntityIdVO,
    ) -> ContactSummaryDTO | None:
        descriptor = await self._resolve_descriptor(tenant_id)
        row = await self._runtime_query_gateway.get_by_id(
            descriptor=descriptor,
            object_id=contact_id.uuid,
        )
        if row is None:
            return None
        return self._row_to_summary(row)

    async def get_summaries(
        self,
        *,
        tenant_id: EntityIdVO,
        contact_ids: Sequence[EntityIdVO],
    ) -> dict[UUID, ContactSummaryDTO]:
        unique_ids = tuple(dict.fromkeys(contact_id.uuid for contact_id in contact_ids))
        if not unique_ids:
            return {}
        descriptor = await self._resolve_descriptor(tenant_id)
        rows = await self._runtime_query_gateway.list(
            descriptor=descriptor,
            filters=(
                self._filter_builder.condition(
                    descriptor=descriptor,
                    field="id",
                    op="in",
                    value=list(unique_ids),
                ),
            ),
        )
        summaries = [self._row_to_summary(row) for row in rows]
        return {summary.id: summary for summary in summaries}

    async def _resolve_descriptor(self, tenant_id: EntityIdVO):
        return await self._runtime_object_resolver.resolve(
            tenant_id=tenant_id,
            object_name=self._OBJECT_NAME,
        )

    @staticmethod
    def _row_to_summary(row: Mapping[str, Any]) -> ContactSummaryDTO:
        return ContactSummaryDTO(
            id=RuntimeContactLookupAdapter._as_uuid(row.get("id")),
            first_name=RuntimeContactLookupAdapter._as_str(row.get("first_name")),
            last_name=RuntimeContactLookupAdapter._as_optional_str(
                row.get("last_name")
            ),
            middle_name=RuntimeContactLookupAdapter._as_optional_str(
                row.get("middle_name")
            ),
            status=RuntimeContactLookupAdapter._as_optional_str(row.get("status")),
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


__all__ = ["RuntimeContactLookupAdapter"]
