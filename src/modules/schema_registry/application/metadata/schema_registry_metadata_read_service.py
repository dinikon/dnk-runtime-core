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


class SchemaRegistryMetadataReadService:
    def __init__(
        self,
        data_source_service: DataSourceService,
        object_service: ObjectService,
    ) -> None:
        self._data_source_service = data_source_service
        self._object_service = object_service

    async def get_required_by_tenant(
        self,
        *,
        tenant_id: EntityIdVO,
    ) -> SchemaRegistryMetadataSnapshot:
        datasource = await self._data_source_service.get_required_by_tenant(
            tenant_id=tenant_id
        )
        objects = await self._object_service.list_by_tenant_id(tenant_id=tenant_id)

        for object_entity in objects:
            if object_entity.tenant_id != tenant_id:
                raise SchemaRegistryMetadataInconsistentError(
                    "schema_registry metadata object has mismatched tenant_id."
                )
            if object_entity.data_source_id != datasource.id:
                raise SchemaRegistryMetadataInconsistentError(
                    "schema_registry metadata object has mismatched data_source_id."
                )

        return SchemaRegistryMetadataSnapshot(
            datasource=datasource,
            objects=tuple(objects),
        )
