from __future__ import annotations

from src.modules.shared import EntityIdVO
from src.modules.schema_registry.domain.datasource.entity import DataSourceEntity
from src.modules.schema_registry.domain.datasource.service import DataSourceService
from src.modules.schema_registry.domain.object.service import ObjectService
from src.modules.schema_registry.domain.field.value_object.field_kind import FieldKind
from src.modules.schema_registry.domain.object.value_object.object_kind import (
    ObjectKind,
)
from src.modules.schema_registry.domain.relation.service import RelationService
from src.modules.schema_registry.domain.seed.schema_seed import SchemaSeed
from src.modules.schema_registry.domain.seed.validated_schema_spec import (
    ValidatedSchemaSpec,
)


class SchemaRegistryMetadataWriteService:
    """Записывает metadata schema_registry после создания или diff схемы."""

    def __init__(
        self,
        data_source_service: DataSourceService,
        object_service: ObjectService,
        relation_service: RelationService,
    ) -> None:
        """Инициализирует сервис доменными сервисами datasource и объектов."""
        self._data_source_service = data_source_service
        self._object_service = object_service
        self._relation_service = relation_service

    async def create_from_seed(
        self,
        *,
        tenant_id: EntityIdVO,
        schema_name: str,
        seed: SchemaSeed | ValidatedSchemaSpec,
    ) -> DataSourceEntity:
        """Создает datasource tenant и полностью записывает объекты из seed."""
        datasource = await self._data_source_service.create(
            tenant_id=tenant_id,
            schema_name=schema_name,
        )
        objects = await self._object_service.replace_all_for_tenant_from_seed(
            tenant_id=tenant_id,
            data_source_id=datasource.id,
            seed=seed,
        )
        if isinstance(seed, ValidatedSchemaSpec):
            await self._relation_service.replace_all_for_tenant_from_spec(
                tenant_id=tenant_id,
                data_source_id=datasource.id,
                schema_spec=seed,
                objects=objects,
            )
        return datasource

    async def replace_from_seed(
        self,
        *,
        tenant_id: EntityIdVO,
        seed: SchemaSeed | ValidatedSchemaSpec,
    ) -> DataSourceEntity:
        """Заменяет metadata объектов tenant по seed, сохраняя текущий datasource."""
        datasource = await self._data_source_service.get_required_by_tenant(
            tenant_id=tenant_id
        )
        await self._relation_service.clear_for_tenant(tenant_id=tenant_id)
        objects = await self._object_service.replace_all_for_tenant_from_seed(
            tenant_id=tenant_id,
            data_source_id=datasource.id,
            seed=seed,
        )
        if isinstance(seed, ValidatedSchemaSpec):
            await self._relation_service.replace_all_for_tenant_from_spec(
                tenant_id=tenant_id,
                data_source_id=datasource.id,
                schema_spec=seed,
                objects=objects,
            )
        return datasource

    async def reconcile_from_spec(
        self,
        *,
        tenant_id: EntityIdVO,
        schema_spec: ValidatedSchemaSpec,
    ) -> DataSourceEntity:
        """Синхронизирует metadata объектов tenant с валидированной спецификацией."""
        datasource = await self._data_source_service.get_required_by_tenant(
            tenant_id=tenant_id
        )
        await self._prune_relations_before_object_reconcile(
            tenant_id=tenant_id,
            schema_spec=schema_spec,
        )
        objects = await self._object_service.reconcile_for_tenant_from_spec(
            tenant_id=tenant_id,
            data_source_id=datasource.id,
            schema_spec=schema_spec,
        )
        reconcile_relations = getattr(
            self._relation_service,
            "reconcile_for_tenant_from_spec",
            None,
        )
        if reconcile_relations is None:
            reconcile_relations = (
                self._relation_service.replace_all_for_tenant_from_spec
            )
        await reconcile_relations(
            tenant_id=tenant_id,
            data_source_id=datasource.id,
            schema_spec=schema_spec,
            objects=objects,
        )
        return datasource

    async def _prune_relations_before_object_reconcile(
        self,
        *,
        tenant_id: EntityIdVO,
        schema_spec: ValidatedSchemaSpec,
    ) -> None:
        """Снимает relation FK metadata до удаления referenced members."""
        prune_relations = getattr(
            self._relation_service,
            "prune_for_retained_members",
            None,
        )
        list_objects = getattr(
            self._object_service,
            "list_by_tenant_id",
            None,
        )
        if prune_relations is None or list_objects is None:
            return

        existing_objects = await list_objects(tenant_id=tenant_id)
        specs_by_plural_name = {
            object_spec.plural_name: object_spec for object_spec in schema_spec.objects
        }
        retained_object_ids = set()
        retained_field_ids = set()
        for object_entity in existing_objects:
            object_spec = specs_by_plural_name.get(object_entity.object_name.plural)
            if object_entity.kind == ObjectKind.CUSTOM:
                retained_object_ids.add(object_entity.id)
                retained_field_ids.update(
                    field_entity.id for field_entity in object_entity.fields
                )
                continue
            if object_spec is None:
                continue
            retained_object_ids.add(object_entity.id)
            spec_field_names = {field_spec.name for field_spec in object_spec.fields}
            retained_field_ids.update(
                field_entity.id
                for field_entity in object_entity.fields
                if field_entity.kind == FieldKind.CUSTOM
                or field_entity.field_name.value in spec_field_names
            )

        await prune_relations(
            tenant_id=tenant_id,
            retained_object_ids=retained_object_ids,
            retained_field_ids=retained_field_ids,
        )
