from __future__ import annotations

from typing import Protocol

from src.modules.schema_registry.application.dto.runtime_object_description import (
    RuntimeFieldDescriptionDTO,
    RuntimeObjectDescriptionDTO,
    RuntimeRelationDescriptionDTO,
)
from src.modules.schema_registry.domain.datasource.service import DataSourceService
from src.modules.schema_registry.domain.error import (
    RuntimeObjectNotFoundError,
    SchemaRegistryMetadataInconsistentError,
)
from src.modules.schema_registry.domain.object.service import ObjectService
from src.modules.schema_registry.domain.relation.service import RelationService
from src.modules.schema_registry.runtime.resolver import (
    RuntimeObjectResolverProtocol,
    SchemaRegistryRuntimeObjectResolver,
)
from src.modules.shared import EntityIdVO


class DescribeRuntimeObjectUseCaseProtocol(Protocol):
    """Порт use case чтения описания runtime-объекта."""

    async def __call__(
        self,
        *,
        tenant_id: EntityIdVO,
        object_name: str,
    ) -> RuntimeObjectDescriptionDTO:
        """Возвращает описание runtime-объекта tenant по singular-имени."""
        ...


class DescribeRuntimeObjectUseCase:
    """Use case чтения runtime metadata объекта через schema_registry."""

    def __init__(
        self,
        data_source_service: DataSourceService,
        object_service: ObjectService,
        relation_service: RelationService | None = None,
        runtime_object_resolver: RuntimeObjectResolverProtocol | None = None,
    ) -> None:
        """Инициализирует use case сервисами datasource и object metadata."""
        self._data_source_service = data_source_service
        self._object_service = object_service
        self._include_relations = (
            relation_service is not None or runtime_object_resolver is not None
        )
        self._runtime_object_resolver = runtime_object_resolver or (
            SchemaRegistryRuntimeObjectResolver(
                data_source_service=data_source_service,
                object_service=object_service,
                relation_service=relation_service,
            )
        )

    async def __call__(
        self,
        *,
        tenant_id: EntityIdVO,
        object_name: str,
    ) -> RuntimeObjectDescriptionDTO:
        """Возвращает описание metadata объекта и проверяет его связность."""
        normalized_object_name = object_name.strip()
        data_source = await self._data_source_service.get_required_by_tenant(
            tenant_id=tenant_id,
        )
        object_entity = await self._object_service.get_by_tenant_and_singular_name(
            tenant_id=tenant_id,
            singular_name=normalized_object_name,
        )
        if object_entity is None:
            raise RuntimeObjectNotFoundError(
                tenant_id=str(tenant_id),
                object_name=normalized_object_name,
            )

        if object_entity.tenant_id != tenant_id:
            raise SchemaRegistryMetadataInconsistentError(
                "schema_registry object metadata has mismatched tenant_id."
            )
        if object_entity.data_source_id != data_source.id:
            raise SchemaRegistryMetadataInconsistentError(
                "schema_registry object metadata has mismatched data_source_id."
            )
        relation_descriptions: tuple[RuntimeRelationDescriptionDTO, ...] = ()
        if self._include_relations:
            descriptor = await self._runtime_object_resolver.resolve(
                tenant_id=tenant_id,
                object_name=normalized_object_name,
            )
            relation_descriptions = tuple(
                RuntimeRelationDescriptionDTO(
                    id=relation.id,
                    name=relation.name,
                    label=relation.label,
                    relation_type=relation.relation_type,
                    source_object=relation.source_object,
                    target_object=relation.target_object,
                    source_relation_name=relation.source_relation_name,
                    target_relation_name=relation.target_relation_name,
                    owning_object=relation.owning_object,
                    fk_field=relation.fk_field,
                    referenced_object=relation.referenced_object,
                    referenced_field=relation.referenced_field,
                    relation_table_name=relation.relation_table_name,
                    source_join_column_name=relation.source_join_column_name,
                    target_join_column_name=relation.target_join_column_name,
                    is_collection=relation.is_collection,
                    is_virtual=relation.is_virtual,
                    is_unique=relation.is_unique,
                    is_required=relation.is_required,
                    kind=relation.kind,
                    settings=dict(relation.settings),
                )
                for relation in descriptor.relations
            )

        return RuntimeObjectDescriptionDTO(
            id=object_entity.id.uuid,
            singular_label=object_entity.object_label.singular,
            plural_label=object_entity.object_label.plural,
            description=object_entity.description,
            kind=object_entity.kind.value,
            fields=tuple(
                RuntimeFieldDescriptionDTO(
                    id=field.id.uuid,
                    field_name=field.field_name.value,
                    label=field.label.value,
                    description=field.description,
                    type=field.field_type.code.value,
                    is_nullable=field.is_nullable,
                    default_value=field.default_value,
                    options=dict(field.options),
                    kind=field.kind.value,
                )
                for field in object_entity.fields
            ),
            relations=relation_descriptions,
        )
