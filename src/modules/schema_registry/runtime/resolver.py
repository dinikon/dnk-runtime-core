from __future__ import annotations

from typing import Protocol

from src.modules.schema_registry.domain.datasource.service import DataSourceService
from src.modules.schema_registry.domain.error import (
    RuntimeObjectDescriptorError,
    RuntimeObjectNotFoundError,
    SchemaRegistryMetadataInconsistentError,
)
from src.modules.schema_registry.domain.object.entity import ObjectEntity
from src.modules.schema_registry.domain.object.service import ObjectService
from src.modules.schema_registry.domain.object.value_object import RuntimeObjectIdVO
from src.modules.schema_registry.domain.relation.entity import RelationEntity
from src.modules.schema_registry.domain.relation.service import RelationService
from src.modules.schema_registry.domain.seed.relation_type import RelationTypeEnum
from src.modules.schema_registry.runtime.descriptor import (
    RuntimeFieldDescriptor,
    RuntimeObjectDescriptor,
    RuntimeRelationDescriptor,
)
from src.modules.shared import EntityIdVO


class RuntimeObjectResolverProtocol(Protocol):
    """Порт преобразования schema_registry metadata в runtime descriptor."""

    async def resolve(
        self,
        tenant_id: EntityIdVO,
        object_name: str,
    ) -> RuntimeObjectDescriptor:
        """Возвращает descriptor runtime-объекта tenant по имени."""
        ...

    async def resolve_by_id(
        self,
        tenant_id: EntityIdVO,
        object_id: RuntimeObjectIdVO,
    ) -> RuntimeObjectDescriptor:
        """Возвращает descriptor runtime-объекта tenant по object_id."""
        ...


class SchemaRegistryRuntimeObjectResolver:
    """Resolver, который строит runtime descriptor из schema_registry metadata."""

    def __init__(
        self,
        data_source_service: DataSourceService,
        object_service: ObjectService,
        relation_service: RelationService | None = None,
    ) -> None:
        """Инициализирует resolver сервисами datasource и object metadata."""
        self._data_source_service = data_source_service
        self._object_service = object_service
        self._relation_service = relation_service

    async def resolve(
        self,
        tenant_id: EntityIdVO,
        object_name: str,
    ) -> RuntimeObjectDescriptor:
        """Собирает descriptor объекта и проверяет consistency metadata.

        Resolver связывает datasource tenant с object metadata, переносит поля в
        immutable runtime descriptors и гарантирует наличие primary key поля `id`.
        """
        normalized_object_name = object_name.strip()
        object_entity = await self._object_service.get_by_tenant_and_singular_name(
            tenant_id=tenant_id,
            singular_name=normalized_object_name,
        )
        if object_entity is None:
            raise RuntimeObjectNotFoundError(
                tenant_id=str(tenant_id),
                object_name=normalized_object_name,
            )
        return await self._build_descriptor(
            tenant_id=tenant_id,
            object_entity=object_entity,
            not_found_label=normalized_object_name,
        )

    async def resolve_by_id(
        self,
        tenant_id: EntityIdVO,
        object_id: RuntimeObjectIdVO,
    ) -> RuntimeObjectDescriptor:
        """Собирает descriptor объекта по object_id и проверяет consistency metadata."""
        object_entity = await self._object_service.get_by_id(object_id=object_id)
        if object_entity is None:
            raise RuntimeObjectNotFoundError(
                tenant_id=str(tenant_id),
                object_name=str(object_id),
            )
        return await self._build_descriptor(
            tenant_id=tenant_id,
            object_entity=object_entity,
            not_found_label=str(object_id),
        )

    async def _build_descriptor(
        self,
        *,
        tenant_id: EntityIdVO,
        object_entity: ObjectEntity,
        not_found_label: str,
    ) -> RuntimeObjectDescriptor:
        datasource = await self._data_source_service.get_required_by_tenant(
            tenant_id=tenant_id,
        )

        if object_entity.tenant_id != tenant_id:
            raise RuntimeObjectNotFoundError(
                tenant_id=str(tenant_id),
                object_name=not_found_label,
            )
        if object_entity.data_source_id != datasource.id:
            raise SchemaRegistryMetadataInconsistentError(
                "schema_registry object metadata has mismatched data_source_id."
            )

        fields = tuple(
            RuntimeFieldDescriptor(
                name=field.field_name.value,
                type_code=field.field_type.code.value,
                is_nullable=field.is_nullable,
                default_value=field.default_value,
                options=dict(field.options),
                settings=dict(field.settings),
                kind=field.kind.value,
            )
            for field in object_entity.fields
        )

        field_names = {field.name for field in fields}
        if "id" not in field_names:
            raise RuntimeObjectDescriptorError(
                "Runtime object descriptor requires an 'id' field."
            )

        relations = await self._build_relation_descriptors(
            tenant_id=tenant_id,
            object_entity=object_entity,
        )

        return RuntimeObjectDescriptor(
            schema_name=datasource.schema_name.value,
            object_name=object_entity.object_name.singular,
            table_name=object_entity.object_name.plural,
            pk="id",
            title_field="id",
            fields=fields,
            relations=relations,
            kind=object_entity.kind.value,
        )

    async def _build_relation_descriptors(
        self,
        *,
        tenant_id: EntityIdVO,
        object_entity: ObjectEntity,
    ) -> tuple[RuntimeRelationDescriptor, ...]:
        """Строит relation descriptors для объекта из relation metadata graph."""
        if self._relation_service is None:
            return ()

        objects = await self._object_service.list_by_tenant_id(tenant_id=tenant_id)
        relations = await self._relation_service.list_by_tenant_id(tenant_id=tenant_id)
        objects_by_id = {item.id: item for item in objects}
        if object_entity.id not in objects_by_id:
            objects_by_id[object_entity.id] = object_entity
        fields_by_id = {
            field.id: field for item in objects_by_id.values() for field in item.fields
        }
        descriptors: list[RuntimeRelationDescriptor] = []

        for relation in relations:
            if (
                relation.source_object_id != object_entity.id
                and relation.target_object_id != object_entity.id
            ):
                continue
            descriptors.append(
                self._map_relation_descriptor(
                    relation=relation,
                    current_object=object_entity,
                    objects_by_id=objects_by_id,
                    fields_by_id=fields_by_id,
                )
            )

        return tuple(descriptors)

    @staticmethod
    def _map_relation_descriptor(
        *,
        relation: RelationEntity,
        current_object: ObjectEntity,
        objects_by_id: dict[RuntimeObjectIdVO, ObjectEntity],
        fields_by_id,
    ) -> RuntimeRelationDescriptor:
        """Мапит RelationEntity в runtime descriptor."""
        source_object = objects_by_id[relation.source_object_id]
        target_object = objects_by_id[relation.target_object_id]
        owning_object = (
            None
            if relation.owning_object_id is None
            else objects_by_id[relation.owning_object_id]
        )
        referenced_object = (
            None
            if relation.referenced_object_id is None
            else objects_by_id[relation.referenced_object_id]
        )
        fk_field = (
            None
            if relation.fk_field_id is None
            else fields_by_id[relation.fk_field_id].field_name.value
        )
        referenced_field = (
            None
            if relation.referenced_field_id is None
            else fields_by_id[relation.referenced_field_id].field_name.value
        )
        return RuntimeRelationDescriptor(
            id=str(relation.id),
            name=relation.name,
            label=relation.label,
            relation_type=relation.relation_type.value,
            source_object=source_object.object_name.plural,
            target_object=target_object.object_name.plural,
            source_relation_name=relation.source_relation_name,
            target_relation_name=relation.target_relation_name,
            owning_object=(
                owning_object.object_name.plural if owning_object is not None else None
            ),
            fk_field=fk_field,
            referenced_object=(
                referenced_object.object_name.plural
                if referenced_object is not None
                else None
            ),
            referenced_field=referenced_field,
            relation_table_name=relation.relation_table_name,
            source_join_column_name=relation.source_join_column_name,
            target_join_column_name=relation.target_join_column_name,
            on_delete=relation.on_delete,
            is_required=relation.is_required,
            is_collection=SchemaRegistryRuntimeObjectResolver._is_collection(
                relation=relation,
                current_object=current_object,
            ),
            is_virtual=SchemaRegistryRuntimeObjectResolver._is_virtual(
                relation=relation,
                current_object=current_object,
            ),
            is_unique=relation.is_unique,
            kind=relation.kind,
            settings=dict(relation.settings),
        )

    @staticmethod
    def _is_collection(
        *,
        relation: RelationEntity,
        current_object: ObjectEntity,
    ) -> bool:
        """Определяет collection-семантику relation для текущей стороны."""
        relation_type = relation.relation_type
        if relation_type == RelationTypeEnum.MANY_TO_MANY:
            return True
        if current_object.id == relation.source_object_id:
            return relation_type == RelationTypeEnum.ONE_TO_MANY
        if current_object.id == relation.target_object_id:
            return relation_type == RelationTypeEnum.MANY_TO_ONE
        return False

    @staticmethod
    def _is_virtual(
        *,
        relation: RelationEntity,
        current_object: ObjectEntity,
    ) -> bool:
        """Проверяет, есть ли физическая FK-колонка на текущем объекте."""
        if relation.relation_type == RelationTypeEnum.MANY_TO_MANY:
            return True
        return relation.owning_object_id != current_object.id
