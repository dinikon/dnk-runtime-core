from __future__ import annotations

from src.modules.schema_registry.domain.error import RuntimeObjectNotFoundError
from src.modules.schema_registry.domain.object.service import ObjectService
from src.modules.schema_registry.runtime import (
    RuntimeObjectDescriptor,
    RuntimeObjectResolverProtocol,
)
from src.modules.segmentation.application.segment_version.query import (
    SegmentVersionRuntimeRelationMetadata,
)
from src.modules.shared import EntityIdVO


class RuntimeObjectMetadataAdapter:
    """Runtime metadata adapter for segment version DSL validation."""

    def __init__(
        self,
        *,
        runtime_object_resolver: RuntimeObjectResolverProtocol,
        object_service: ObjectService,
    ) -> None:
        self._runtime_object_resolver = runtime_object_resolver
        self._object_service = object_service

    async def resolve_object(
        self,
        *,
        tenant_id: EntityIdVO,
        object_name: str,
    ) -> RuntimeObjectDescriptor:
        try:
            return await self._runtime_object_resolver.resolve(
                tenant_id=tenant_id,
                object_name=object_name,
            )
        except RuntimeObjectNotFoundError as exc:
            raise LookupError(str(exc)) from exc

    async def field_exists(
        self,
        *,
        tenant_id: EntityIdVO,
        object_name: str,
        field_name: str,
    ) -> bool:
        return (
            await self.field_type(
                tenant_id=tenant_id,
                object_name=object_name,
                field_name=field_name,
            )
            is not None
        )

    async def field_type(
        self,
        *,
        tenant_id: EntityIdVO,
        object_name: str,
        field_name: str,
    ) -> str | None:
        try:
            descriptor = await self.resolve_object(
                tenant_id=tenant_id,
                object_name=object_name,
            )
        except LookupError:
            return None
        field = descriptor.field_by_name(field_name)
        return None if field is None else field.type_code

    async def resolve_relation(
        self,
        *,
        tenant_id: EntityIdVO,
        source_object: str,
        relation_name: str,
    ) -> SegmentVersionRuntimeRelationMetadata | None:
        try:
            descriptor = await self.resolve_object(
                tenant_id=tenant_id,
                object_name=source_object,
            )
        except LookupError:
            return None

        plural_to_singular = await self._plural_to_singular(tenant_id=tenant_id)
        current_plural = descriptor.table_name
        normalized_relation_name = relation_name.strip()

        for relation in descriptor.relations:
            if (
                relation.source_object == current_plural
                and normalized_relation_name
                in {
                    relation.name,
                    relation.source_relation_name,
                }
            ):
                return SegmentVersionRuntimeRelationMetadata(
                    name=normalized_relation_name,
                    source_object=descriptor.object_name,
                    target_object=plural_to_singular.get(
                        relation.target_object,
                        relation.target_object,
                    ),
                    relation_type=relation.relation_type,
                    fk_field=relation.fk_field,
                    referenced_object=self._public_object_name(
                        relation.referenced_object,
                        plural_to_singular=plural_to_singular,
                    ),
                    referenced_field=relation.referenced_field,
                    owning_object=self._public_object_name(
                        relation.owning_object,
                        plural_to_singular=plural_to_singular,
                    ),
                )
            if (
                relation.target_object == current_plural
                and normalized_relation_name
                in {
                    relation.name,
                    relation.target_relation_name,
                }
            ):
                return SegmentVersionRuntimeRelationMetadata(
                    name=normalized_relation_name,
                    source_object=descriptor.object_name,
                    target_object=plural_to_singular.get(
                        relation.source_object,
                        relation.source_object,
                    ),
                    relation_type=relation.relation_type,
                    fk_field=relation.fk_field,
                    referenced_object=self._public_object_name(
                        relation.referenced_object,
                        plural_to_singular=plural_to_singular,
                    ),
                    referenced_field=relation.referenced_field,
                    owning_object=self._public_object_name(
                        relation.owning_object,
                        plural_to_singular=plural_to_singular,
                    ),
                )
        return None

    async def relation_exists(
        self,
        *,
        tenant_id: EntityIdVO,
        source_object: str,
        relation_name: str,
    ) -> bool:
        return (
            await self.resolve_relation(
                tenant_id=tenant_id,
                source_object=source_object,
                relation_name=relation_name,
            )
            is not None
        )

    async def _plural_to_singular(self, *, tenant_id: EntityIdVO) -> dict[str, str]:
        objects = await self._object_service.list_by_tenant_id(tenant_id=tenant_id)
        return {item.object_name.plural: item.object_name.singular for item in objects}

    @staticmethod
    def _public_object_name(
        value: str | None,
        *,
        plural_to_singular: dict[str, str],
    ) -> str | None:
        if value is None:
            return None
        return plural_to_singular.get(value, value)


__all__ = ["RuntimeObjectMetadataAdapter"]
