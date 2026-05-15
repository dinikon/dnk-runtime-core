from __future__ import annotations

from src.modules.shared import EntityIdVO
from src.modules.schema_registry.application.metadata.schema_registry_metadata_snapshot import (
    SchemaRegistryMetadataSnapshot,
)
from src.modules.schema_registry.domain.datasource.service import DataSourceService
from src.modules.schema_registry.domain.error import (
    SchemaRegistryMetadataInconsistentError,
)
from src.modules.schema_registry.domain.object.service import ObjectService
from src.modules.schema_registry.domain.relation.service import RelationService

class SchemaRegistryMetadataReadService:
    """Собирает сохраненную metadata-картину schema_registry для tenant."""

    def __init__(
        self,
        data_source_service: DataSourceService,
        object_service: ObjectService,
        relation_service: RelationService,
    ) -> None:
        """Инициализирует сервис зависимостями для чтения datasource и объектов."""
        self._data_source_service = data_source_service
        self._object_service = object_service
        self._relation_service = relation_service

    async def get_required_by_tenant(
        self,
        *,
        tenant_id: EntityIdVO,
    ) -> SchemaRegistryMetadataSnapshot:
        """Возвращает обязательный snapshot metadata и проверяет его связность."""
        datasource = await self._data_source_service.get_required_by_tenant(
            tenant_id=tenant_id
        )
        objects = await self._object_service.list_by_tenant_id(tenant_id=tenant_id)
        relations = await self._relation_service.list_by_tenant_id(tenant_id=tenant_id)

        for object_entity in objects:
            if object_entity.tenant_id != tenant_id:
                raise SchemaRegistryMetadataInconsistentError(
                    "schema_registry metadata object has mismatched tenant_id."
                )
            if object_entity.data_source_id != datasource.id:
                raise SchemaRegistryMetadataInconsistentError(
                    "schema_registry metadata object has mismatched data_source_id."
                )
        object_ids = {object_entity.id for object_entity in objects}
        field_ids = {
            field_entity.id
            for object_entity in objects
            for field_entity in object_entity.fields
        }
        for relation in relations:
            if relation.tenant_id != tenant_id:
                raise SchemaRegistryMetadataInconsistentError(
                    "schema_registry metadata relation has mismatched tenant_id."
                )
            if relation.data_source_id != datasource.id:
                raise SchemaRegistryMetadataInconsistentError(
                    "schema_registry metadata relation has mismatched data_source_id."
                )
            relation_object_ids = {
                relation.source_object_id,
                relation.target_object_id,
                relation.owning_object_id,
                relation.referenced_object_id,
            } - {None}
            if relation_object_ids - object_ids:
                raise SchemaRegistryMetadataInconsistentError(
                    "schema_registry metadata relation references unknown object."
                )
            relation_field_ids = {
                relation.fk_field_id,
                relation.referenced_field_id,
            } - {None}
            if relation_field_ids - field_ids:
                raise SchemaRegistryMetadataInconsistentError(
                    "schema_registry metadata relation references unknown field."
                )

        return SchemaRegistryMetadataSnapshot(
            datasource=datasource,
            objects=tuple(objects),
            relations=tuple(relations),
        )
