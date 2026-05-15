from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

from src.modules.schema_registry.domain.datasource.value_object import DataSourceIdVO
from src.modules.schema_registry.domain.field.entity import FieldEntity
from src.modules.schema_registry.domain.object.entity import ObjectEntity
from src.modules.schema_registry.domain.object.value_object import RuntimeObjectIdVO
from src.modules.schema_registry.domain.relation.entity import RelationEntity
from src.modules.schema_registry.domain.relation.repository import (
    RelationRepositoryProtocol,
)
from src.modules.schema_registry.domain.relation.value_object import RuntimeRelationIdVO
from src.modules.schema_registry.domain.seed.validated_schema_spec import (
    ValidatedRelationSpec,
    ValidatedSchemaSpec,
)
from src.modules.shared import ClockPort, EntityIdVO


class RelationService:
    """Доменный сервис для создания и синхронизации runtime relation metadata."""

    def __init__(
        self,
        *,
        relation_repository: RelationRepositoryProtocol,
        clock: ClockPort,
        relation_id_provider: Callable[[], RuntimeRelationIdVO],
    ) -> None:
        """Инициализирует сервис репозиторием, временем и id provider."""
        self._relation_repository = relation_repository
        self._clock = clock
        self._relation_id_provider = relation_id_provider

    async def replace_all_for_tenant_from_spec(
        self,
        *,
        tenant_id: EntityIdVO,
        data_source_id: DataSourceIdVO,
        schema_spec: ValidatedSchemaSpec,
        objects: list[ObjectEntity],
    ) -> list[RelationEntity]:
        """Полностью заменяет relation metadata tenant из валидированной spec."""
        relations = self._build_relation_entities(
            tenant_id=tenant_id,
            data_source_id=data_source_id,
            schema_spec=schema_spec,
            objects=objects,
            existing_by_name={},
        )
        await self._relation_repository.replace_all_for_tenant(
            tenant_id=tenant_id,
            relations=relations,
        )
        return relations

    async def clear_for_tenant(
        self,
        *,
        tenant_id: EntityIdVO,
    ) -> None:
        """Удаляет всю relation metadata tenant."""
        await self._relation_repository.clear_for_tenant(tenant_id=tenant_id)

    async def reconcile_for_tenant_from_spec(
        self,
        *,
        tenant_id: EntityIdVO,
        data_source_id: DataSourceIdVO,
        schema_spec: ValidatedSchemaSpec,
        objects: list[ObjectEntity],
    ) -> list[RelationEntity]:
        """Синхронизирует relation metadata tenant с валидированной spec."""
        existing_relations = await self._relation_repository.list_by_tenant_id(
            tenant_id=tenant_id
        )
        existing_by_name = {relation.name: relation for relation in existing_relations}
        relations = self._build_relation_entities(
            tenant_id=tenant_id,
            data_source_id=data_source_id,
            schema_spec=schema_spec,
            objects=objects,
            existing_by_name=existing_by_name,
        )
        spec_relation_names = {relation.name for relation in relations}
        for relation in existing_relations:
            if relation.kind == "custom" and relation.name not in spec_relation_names:
                relations.append(relation)

        await self._relation_repository.reconcile_for_tenant(
            tenant_id=tenant_id,
            relations=relations,
        )
        return relations

    async def list_by_tenant_id(
        self,
        *,
        tenant_id: EntityIdVO,
    ) -> list[RelationEntity]:
        """Возвращает все relation metadata tenant."""
        return await self._relation_repository.list_by_tenant_id(tenant_id=tenant_id)

    def _build_relation_entities(
        self,
        *,
        tenant_id: EntityIdVO,
        data_source_id: DataSourceIdVO,
        schema_spec: ValidatedSchemaSpec,
        objects: list[ObjectEntity],
        existing_by_name: dict[str, RelationEntity],
    ) -> list[RelationEntity]:
        """Мапит relation specs в domain entities, переиспользуя id при reconcile."""
        now = self._clock.now()
        objects_by_name = self._objects_by_name(objects)
        fields_by_object_and_name = self._fields_by_object_and_name(objects)
        relations: list[RelationEntity] = []

        for object_spec in schema_spec.objects:
            for relation_spec in object_spec.relations:
                existing_relation = existing_by_name.get(relation_spec.name)
                relation_id = (
                    existing_relation.id
                    if existing_relation is not None
                    else self._relation_id_provider()
                )
                created_at = (
                    existing_relation.created_at
                    if existing_relation is not None
                    else now
                )
                relation = self._build_relation_entity(
                    relation_spec=relation_spec,
                    tenant_id=tenant_id,
                    data_source_id=data_source_id,
                    objects_by_name=objects_by_name,
                    fields_by_object_and_name=fields_by_object_and_name,
                    relation_id=relation_id,
                    created_at=created_at,
                    updated_at=now,
                )
                relations.append(relation)

        return relations

    @staticmethod
    def _build_relation_entity(
        *,
        relation_spec: ValidatedRelationSpec,
        tenant_id: EntityIdVO,
        data_source_id: DataSourceIdVO,
        objects_by_name: dict[str, ObjectEntity],
        fields_by_object_and_name: dict[tuple[RuntimeObjectIdVO, str], FieldEntity],
        relation_id: RuntimeRelationIdVO,
        created_at: datetime,
        updated_at: datetime,
    ) -> RelationEntity:
        """Мапит один relation spec в RelationEntity."""
        source_object = objects_by_name[relation_spec.source_object]
        target_object = objects_by_name[relation_spec.target_object]
        owning_object = (
            None
            if relation_spec.owning_object is None
            else objects_by_name[relation_spec.owning_object]
        )
        referenced_object = (
            None
            if relation_spec.referenced_object is None
            else objects_by_name[relation_spec.referenced_object]
        )
        fk_field = None
        if owning_object is not None and relation_spec.fk_field is not None:
            fk_field = fields_by_object_and_name[
                (owning_object.id, relation_spec.fk_field)
            ]
        referenced_field = None
        if referenced_object is not None and relation_spec.referenced_field is not None:
            referenced_field = fields_by_object_and_name[
                (referenced_object.id, relation_spec.referenced_field)
            ]

        return RelationEntity(
            id=relation_id,
            created_at=created_at,
            updated_at=updated_at,
            tenant_id=tenant_id,
            data_source_id=data_source_id,
            name=relation_spec.name,
            relation_type=relation_spec.relation_type,
            source_object_id=source_object.id,
            target_object_id=target_object.id,
            owning_object_id=owning_object.id if owning_object is not None else None,
            fk_field_id=fk_field.id if fk_field is not None else None,
            referenced_object_id=(
                referenced_object.id if referenced_object is not None else None
            ),
            referenced_field_id=(
                referenced_field.id if referenced_field is not None else None
            ),
            source_relation_name=relation_spec.source_relation_name,
            target_relation_name=relation_spec.target_relation_name,
            relation_table_name=relation_spec.relation_table_name,
            source_join_column_name=relation_spec.source_join_column_name,
            target_join_column_name=relation_spec.target_join_column_name,
            on_delete=relation_spec.on_delete,
            is_required=relation_spec.is_required,
            is_unique=relation_spec.is_unique,
            kind=relation_spec.kind,
            settings=relation_spec.settings,
        )

    @staticmethod
    def _objects_by_name(objects: list[ObjectEntity]) -> dict[str, ObjectEntity]:
        """Строит lookup объектов по singular и plural именам."""
        mapping: dict[str, ObjectEntity] = {}
        for object_entity in objects:
            mapping[object_entity.object_name.singular] = object_entity
            mapping[object_entity.object_name.plural] = object_entity
        return mapping

    @staticmethod
    def _fields_by_object_and_name(
        objects: list[ObjectEntity],
    ) -> dict[tuple[RuntimeObjectIdVO, str], FieldEntity]:
        """Строит lookup field metadata по object id и field name."""
        mapping: dict[tuple[RuntimeObjectIdVO, str], FieldEntity] = {}
        for object_entity in objects:
            for field_entity in object_entity.fields:
                mapping[(object_entity.id, field_entity.field_name.value)] = (
                    field_entity
                )
        return mapping
