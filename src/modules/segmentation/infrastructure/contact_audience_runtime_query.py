from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any
from uuid import UUID

from src.modules.runtime_data.application.models import (
    PageSpec,
    SortSpec,
    TypedFilterExpression,
)
from src.modules.runtime_data.application.ports import RuntimeQueryGateway
from src.modules.schema_registry.runtime import (
    RuntimeObjectDescriptor,
    RuntimeObjectResolverProtocol,
)
from src.modules.segmentation.application.segment_version.dsl import (
    SegmentVersionContactMapping,
)
from src.modules.segmentation.application.segment_version.evaluation import (
    SegmentVersionEvaluationInvalidMappingError,
    SegmentVersionEvaluationUnsupportedRelationPathError,
)
from src.modules.segmentation.application.segment_version.query import (
    ContactAudienceQueryProtocol,
)
from src.modules.shared import EntityIdVO


class RuntimeContactAudienceQuery(ContactAudienceQueryProtocol):
    """Runtime query adapter that maps dynamic rule rows to Contact ids."""

    def __init__(
        self,
        *,
        runtime_object_resolver: RuntimeObjectResolverProtocol,
        runtime_query_gateway: RuntimeQueryGateway,
    ) -> None:
        self._runtime_object_resolver = runtime_object_resolver
        self._runtime_query_gateway = runtime_query_gateway

    async def list_contact_ids(
        self,
        *,
        tenant_id: EntityIdVO,
        object_name: str,
        filters: Sequence[TypedFilterExpression],
        relation_path: Sequence[str],
        contact_mapping: SegmentVersionContactMapping,
        limit: int | None = None,
        offset: int = 0,
    ) -> tuple[UUID, ...]:
        self._assert_supported_mapping(
            object_name=object_name,
            relation_path=relation_path,
            contact_mapping=contact_mapping,
        )
        descriptor = await self._resolve_descriptor(
            tenant_id=tenant_id,
            object_name=object_name,
        )
        rows = await self._runtime_query_gateway.list(
            descriptor=descriptor,
            filters=filters,
            sorting=(SortSpec(field="id", direction="asc"),),
            page=None if limit is None else PageSpec(limit=limit, offset=offset),
        )
        return tuple(
            self._row_to_contact_id(
                row=row,
                contact_mapping=contact_mapping,
            )
            for row in rows
        )

    async def _resolve_descriptor(
        self,
        *,
        tenant_id: EntityIdVO,
        object_name: str,
    ) -> RuntimeObjectDescriptor:
        return await self._runtime_object_resolver.resolve(
            tenant_id=tenant_id,
            object_name=object_name,
        )

    @staticmethod
    def _assert_supported_mapping(
        *,
        object_name: str,
        relation_path: Sequence[str],
        contact_mapping: SegmentVersionContactMapping,
    ) -> None:
        if object_name == "contact":
            if relation_path or contact_mapping.type != "self":
                raise SegmentVersionEvaluationUnsupportedRelationPathError(
                    "Contact self rules must use empty relation_path and self mapping."
                )
            return

        if len(relation_path) != 1 or contact_mapping.type != "field":
            raise SegmentVersionEvaluationUnsupportedRelationPathError(
                "Only direct related-object rules with field contact mapping are supported."
            )

    @staticmethod
    def _row_to_contact_id(
        *,
        row: Mapping[str, Any],
        contact_mapping: SegmentVersionContactMapping,
    ) -> UUID:
        field_name = "id" if contact_mapping.type == "self" else contact_mapping.field
        if field_name not in row or row.get(field_name) is None:
            raise SegmentVersionEvaluationInvalidMappingError(
                f"Runtime row does not contain contact mapping field '{field_name}'."
            )
        try:
            return RuntimeContactAudienceQuery._as_uuid(row.get(field_name))
        except (TypeError, ValueError) as exc:
            raise SegmentVersionEvaluationInvalidMappingError(
                f"Runtime row field '{field_name}' is not a valid Contact id."
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


__all__ = ["RuntimeContactAudienceQuery"]
