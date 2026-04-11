from __future__ import annotations

from src.modules.shared import EntityIdVO
from src.modules.schema_registry.domain.datasource.entity import DataSourceEntity
from src.modules.schema_registry.domain.datasource.service import DataSourceService
from src.modules.schema_registry.domain.object.service import ObjectService
from src.modules.schema_registry.domain.seed.schema_seed import SchemaSeed
from src.modules.schema_registry.domain.seed.validated_schema_spec import (
    ValidatedSchemaSpec,
)


class SchemaRegistryMetadataWriteService:
    def __init__(
        self,
        data_source_service: DataSourceService,
        object_service: ObjectService,
    ) -> None:
        self._data_source_service = data_source_service
        self._object_service = object_service

    async def create_from_seed(
        self,
        *,
        tenant_id: EntityIdVO,
        schema_name: str,
        seed: SchemaSeed | ValidatedSchemaSpec,
    ) -> DataSourceEntity:
        datasource = await self._data_source_service.create(
            tenant_id=tenant_id,
            schema_name=schema_name,
        )
        await self._object_service.replace_all_for_tenant_from_seed(
            tenant_id=tenant_id,
            data_source_id=datasource.id,
            seed=seed,
        )
        return datasource

    async def replace_from_seed(
        self,
        *,
        tenant_id: EntityIdVO,
        seed: SchemaSeed | ValidatedSchemaSpec,
    ) -> DataSourceEntity:
        datasource = await self._data_source_service.get_required_by_tenant(
            tenant_id=tenant_id
        )
        await self._object_service.replace_all_for_tenant_from_seed(
            tenant_id=tenant_id,
            data_source_id=datasource.id,
            seed=seed,
        )
        return datasource

    async def reconcile_from_spec(
        self,
        *,
        tenant_id: EntityIdVO,
        schema_spec: ValidatedSchemaSpec,
    ) -> DataSourceEntity:
        datasource = await self._data_source_service.get_required_by_tenant(
            tenant_id=tenant_id
        )
        await self._object_service.reconcile_for_tenant_from_spec(
            tenant_id=tenant_id,
            data_source_id=datasource.id,
            schema_spec=schema_spec,
        )
        return datasource
