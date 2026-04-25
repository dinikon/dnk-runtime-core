from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

from src.modules.shared import ClockPort, EntityIdVO
from src.modules.schema_registry.domain.field.entity import FieldEntity
from src.modules.schema_registry.domain.field.type_catalog import FieldTypeCatalog
from src.modules.schema_registry.domain.field.value_object.field_label import (
    FieldLabelVO,
)
from src.modules.schema_registry.domain.field.value_object.field_name import FieldNameVO
from src.modules.schema_registry.domain.object.entity import ObjectEntity
from src.modules.schema_registry.domain.object.repository import (
    ObjectRepositoryProtocol,
)
from src.modules.schema_registry.domain.object.value_object.object_label import (
    ObjectLabelVO,
)
from src.modules.schema_registry.domain.object.value_object.object_kind import (
    ObjectKind,
)
from src.modules.schema_registry.domain.object.value_object.object_name import (
    ObjectNameVO,
)
from src.modules.schema_registry.domain.seed.field_seed import FieldSeed
from src.modules.schema_registry.domain.seed.schema_seed import SchemaSeed
from src.modules.schema_registry.domain.seed.validated_schema_spec import (
    ValidatedFieldSpec,
    ValidatedSchemaSpec,
)


class ObjectService:
    """Доменный сервис для создания и синхронизации runtime object metadata."""

    def __init__(
        self,
        object_repository: ObjectRepositoryProtocol,
        clock: ClockPort,
        id_provider: Callable[[], EntityIdVO],
        field_type_catalog: FieldTypeCatalog,
    ) -> None:
        """Инициализирует сервис репозиторием, временем, id и каталогом типов."""
        self._object_repository = object_repository
        self._clock = clock
        self._id_provider = id_provider
        self._field_type_catalog = field_type_catalog

    async def replace_all_for_tenant_from_seed(
        self,
        *,
        tenant_id: EntityIdVO,
        data_source_id: EntityIdVO,
        seed: SchemaSeed | ValidatedSchemaSpec,
    ) -> list[ObjectEntity]:
        """Полностью пересоздает metadata объектов tenant из seed или spec."""
        now = self._clock.now()
        objects: list[ObjectEntity] = []

        if isinstance(seed, ValidatedSchemaSpec):
            for object_spec in seed.objects:
                object_entity = self._create_object_entity(
                    tenant_id=tenant_id,
                    data_source_id=data_source_id,
                    now=now,
                    singular_name=object_spec.singular_name,
                    plural_name=object_spec.plural_name,
                    singular_label=object_spec.singular_label,
                    plural_label=object_spec.plural_label,
                    description=object_spec.description,
                    kind=object_spec.kind,
                )
                self._append_fields_from_spec(
                    object_entity=object_entity,
                    field_specs=object_spec.fields,
                    now=now,
                )
                objects.append(object_entity)
        else:
            for object_seed in seed.objects:
                object_entity = self._create_object_entity(
                    tenant_id=tenant_id,
                    data_source_id=data_source_id,
                    now=now,
                    singular_name=object_seed.singular_name,
                    plural_name=object_seed.plural_name,
                    singular_label=object_seed.singular_label,
                    plural_label=object_seed.plural_label,
                    description=object_seed.description,
                    kind=ObjectKind.from_value(object_seed.kind),
                )
                self._append_fields_from_seed(
                    object_entity=object_entity,
                    field_seeds=object_seed.fields,
                    now=now,
                )
                objects.append(object_entity)

        await self._object_repository.replace_all_for_tenant(
            tenant_id=tenant_id,
            objects=objects,
        )
        return objects

    async def reconcile_for_tenant_from_spec(
        self,
        *,
        tenant_id: EntityIdVO,
        data_source_id: EntityIdVO,
        schema_spec: ValidatedSchemaSpec,
    ) -> list[ObjectEntity]:
        """Синхронизирует существующие объекты tenant с валидированной spec.

        Существующие объекты переиспользуются по plural-имени, поля обновляются
        по имени, а отсутствующие в spec поля удаляются из metadata через
        финальный список reconciled_fields.
        """
        now = self._clock.now()
        existing_objects = await self._object_repository.list_by_tenant_id(
            tenant_id=tenant_id
        )
        existing_by_plural_name = {
            object_entity.object_name.plural: object_entity
            for object_entity in existing_objects
        }
        objects: list[ObjectEntity] = []

        for object_spec in schema_spec.objects:
            object_entity = existing_by_plural_name.get(object_spec.plural_name)
            if object_entity is None:
                object_entity = ObjectEntity.create(
                    id_=self._id_provider(),
                    tenant_id=tenant_id,
                    data_source_id=data_source_id,
                    now=now,
                    object_name=ObjectNameVO(
                        singular=object_spec.singular_name,
                        plural=object_spec.plural_name,
                    ),
                    object_label=ObjectLabelVO(
                        singular=object_spec.singular_label,
                        plural=object_spec.plural_label,
                    ),
                    description=object_spec.description,
                    kind=object_spec.kind,
                )
                self._reconcile_fields(
                    object_entity=object_entity,
                    field_specs=object_spec.fields,
                    now=now,
                )
            else:
                self._update_object_metadata(
                    object_entity=object_entity,
                    now=now,
                    object_name=ObjectNameVO(
                        singular=object_spec.singular_name,
                        plural=object_spec.plural_name,
                    ),
                    object_label=ObjectLabelVO(
                        singular=object_spec.singular_label,
                        plural=object_spec.plural_label,
                    ),
                    description=object_spec.description,
                    kind=object_spec.kind,
                )
                if self._reconcile_fields(
                    object_entity=object_entity,
                    field_specs=object_spec.fields,
                    now=now,
                ):
                    object_entity.updated_at = now

            objects.append(object_entity)

        await self._object_repository.reconcile_for_tenant(
            tenant_id=tenant_id,
            objects=objects,
        )
        return objects

    async def list_by_tenant_id(
        self,
        *,
        tenant_id: EntityIdVO,
    ) -> list[ObjectEntity]:
        """Возвращает все runtime-объекты tenant из репозитория."""
        return await self._object_repository.list_by_tenant_id(tenant_id=tenant_id)

    async def get_by_tenant_and_singular_name(
        self,
        *,
        tenant_id: EntityIdVO,
        singular_name: str,
    ) -> ObjectEntity | None:
        """Возвращает runtime-объект tenant по singular-имени или None."""
        return await self._object_repository.get_by_tenant_and_singular_name(
            tenant_id=tenant_id,
            singular_name=singular_name,
        )

    def _reconcile_fields(
        self,
        *,
        object_entity: ObjectEntity,
        field_specs: tuple[ValidatedFieldSpec, ...],
        now: datetime,
    ) -> bool:
        """Сверяет поля объекта со spec и возвращает факт изменения metadata."""
        existing_by_name = {
            field.field_name.value: field for field in object_entity.fields
        }
        reconciled_fields: list[FieldEntity] = []
        changed = len(existing_by_name) != len(field_specs)

        for field_spec in field_specs:
            field_entity = existing_by_name.get(field_spec.name)
            if field_entity is None:
                field_entity = FieldEntity.create(
                    id_=self._id_provider(),
                    object_id=object_entity.id,
                    now=now,
                    field_name=FieldNameVO(field_spec.name),
                    field_type=field_spec.field_type,
                    kind=field_spec.kind,
                    label=FieldLabelVO(field_spec.label),
                    description=field_spec.description,
                    is_nullable=field_spec.is_nullable,
                    default_value=field_spec.default,
                    options=field_spec.options,
                    settings=field_spec.settings,
                )
                changed = True
            else:
                changed = (
                    field_entity.update_from_spec(
                        now=now,
                        field_name=FieldNameVO(field_spec.name),
                        field_type=field_spec.field_type,
                        kind=field_spec.kind,
                        label=FieldLabelVO(field_spec.label),
                        description=field_spec.description,
                        is_nullable=field_spec.is_nullable,
                        default_value=field_spec.default,
                        options=field_spec.options,
                        settings=field_spec.settings,
                    )
                    or changed
                )
            reconciled_fields.append(field_entity)

        if object_entity.fields != reconciled_fields:
            object_entity.fields = reconciled_fields
            changed = True
        return changed

    def _create_object_entity(
        self,
        *,
        tenant_id: EntityIdVO,
        data_source_id: EntityIdVO,
        now: datetime,
        singular_name: str,
        plural_name: str,
        singular_label: str,
        plural_label: str,
        description: str,
        kind: ObjectKind,
    ) -> ObjectEntity:
        """Создает ObjectEntity с новыми id/timestamps и валидированными VO."""
        return ObjectEntity.create(
            id_=self._id_provider(),
            tenant_id=tenant_id,
            data_source_id=data_source_id,
            now=now,
            object_name=ObjectNameVO(
                singular=singular_name,
                plural=plural_name,
            ),
            object_label=ObjectLabelVO(
                singular=singular_label,
                plural=plural_label,
            ),
            description=description,
            kind=kind,
        )

    def _append_fields_from_seed(
        self,
        *,
        object_entity: ObjectEntity,
        field_seeds: tuple[FieldSeed, ...],
        now: datetime,
    ) -> None:
        """Добавляет поля в объект напрямую из raw field seed."""
        object_entity.add_fields_from_seed(
            now=now,
            seeds=field_seeds,
            field_id_provider=self._id_provider,
            field_type_mapper=self._field_type_catalog.from_seed_type,
        )

    def _append_fields_from_spec(
        self,
        *,
        object_entity: ObjectEntity,
        field_specs: tuple[ValidatedFieldSpec, ...],
        now: datetime,
    ) -> None:
        """Добавляет поля в объект из валидированной field spec."""
        for field_spec in field_specs:
            object_entity.add_field(
                field_id=self._id_provider(),
                now=now,
                field_name=field_spec.name,
                field_type=field_spec.field_type,
                label=field_spec.label,
                description=field_spec.description,
                is_nullable=field_spec.is_nullable,
                default_value=field_spec.default,
                options=field_spec.options,
                settings=field_spec.settings,
                kind=field_spec.kind,
            )

    @staticmethod
    def _update_object_metadata(
        *,
        object_entity: ObjectEntity,
        now: datetime,
        object_name: ObjectNameVO,
        object_label: ObjectLabelVO,
        description: str,
        kind: ObjectKind,
    ) -> None:
        """Обновляет metadata объекта, если имя, label или description изменились."""
        normalized_description = description.strip()
        if (
            object_entity.object_name == object_name
            and object_entity.object_label == object_label
            and object_entity.description == normalized_description
            and object_entity.kind == kind
        ):
            return
        object_entity.rename(
            now=now,
            object_name=object_name,
            object_label=object_label,
            description=normalized_description,
            kind=kind,
        )
