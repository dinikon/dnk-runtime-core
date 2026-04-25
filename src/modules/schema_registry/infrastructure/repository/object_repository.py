from __future__ import annotations

from collections import defaultdict
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.shared import EntityIdVO
from src.modules.schema_registry.domain.field.entity import FieldEntity
from src.modules.schema_registry.domain.field.enum.field_type import FieldTypeEnum
from src.modules.schema_registry.domain.field.value_object.field_kind import FieldKind
from src.modules.schema_registry.domain.field.value_object.field_label import (
    FieldLabelVO,
)
from src.modules.schema_registry.domain.field.value_object.field_name import FieldNameVO
from src.modules.schema_registry.domain.field.value_object.field_type import FieldTypeVO
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
from src.modules.schema_registry.infrastructure.persistence.field import FieldORM
from src.modules.schema_registry.infrastructure.persistence.object import ObjectORM


class SqlAlchemyObjectRepository(ObjectRepositoryProtocol):
    """SQLAlchemy-репозиторий runtime object metadata и связанных fields."""

    def __init__(self, session: AsyncSession) -> None:
        """Инициализирует репозиторий текущей async-сессией."""
        self._session = session

    async def get_by_tenant_and_singular_name(
        self,
        *,
        tenant_id: EntityIdVO,
        singular_name: str,
    ) -> ObjectEntity | None:
        """Ищет runtime-объект tenant по singular-имени и подгружает поля."""
        model = await self._session.scalar(
            select(ObjectORM)
            .where(ObjectORM.tenant_id == tenant_id.value)
            .where(ObjectORM.singular_name == singular_name.strip())
            .limit(1)
        )
        if model is None:
            return None

        field_models = await self._load_fields([model.id])
        return self._map_model(model, field_models.get(model.id, []))

    async def get_by_tenant_and_plural_name(
        self,
        *,
        tenant_id: EntityIdVO,
        plural_name: str,
    ) -> ObjectEntity | None:
        """Ищет runtime-объект tenant по plural-имени и подгружает поля."""
        model = await self._session.scalar(
            select(ObjectORM)
            .where(ObjectORM.tenant_id == tenant_id.value)
            .where(ObjectORM.plural_name == plural_name.strip())
            .limit(1)
        )
        if model is None:
            return None

        field_models = await self._load_fields([model.id])
        return self._map_model(model, field_models.get(model.id, []))

    async def get_by_id(self, *, object_id: EntityIdVO) -> ObjectEntity | None:
        """Ищет runtime-объект по id и подгружает поля."""
        model = await self._session.get(ObjectORM, object_id.value)
        if model is None:
            return None

        field_models = await self._load_fields([model.id])
        return self._map_model(model, field_models.get(model.id, []))

    async def save(self, object_entity: ObjectEntity) -> None:
        """Сохраняет один объект, заменяя набор его field-моделей."""
        await self._session.execute(
            delete(FieldORM).where(FieldORM.object_id == object_entity.id.value)
        )
        await self._session.flush()

        model = await self._session.get(ObjectORM, object_entity.id.value)
        if model is None:
            model = self._to_model(object_entity)
            self._session.add(model)
        else:
            model.tenant_id = object_entity.tenant_id.value
            model.data_source_id = object_entity.data_source_id.value
            model.kind = object_entity.kind.value
            model.singular_name = object_entity.object_name.singular
            model.plural_name = object_entity.object_name.plural
            model.singular_label = object_entity.object_label.singular
            model.plural_label = object_entity.object_label.plural
            model.description = object_entity.description
            model.updated_at = object_entity.updated_at

        await self._session.flush()

        for field_entity in object_entity.fields:
            self._session.add(self._to_field_model(field_entity))

        await self._session.flush()

    async def list_by_tenant_id(
        self,
        *,
        tenant_id: EntityIdVO,
    ) -> list[ObjectEntity]:
        """Возвращает все runtime-объекты tenant с полями в стабильном порядке."""
        models = (
            await self._session.scalars(
                select(ObjectORM)
                .where(ObjectORM.tenant_id == tenant_id.value)
                .order_by(ObjectORM.created_at, ObjectORM.id)
            )
        ).all()
        if not models:
            return []

        field_models = await self._load_fields([model.id for model in models])
        return [
            self._map_model(model, field_models.get(model.id, [])) for model in models
        ]

    async def replace_all_for_tenant(
        self,
        *,
        tenant_id: EntityIdVO,
        objects: list[ObjectEntity],
    ) -> None:
        """Полностью заменяет object/field metadata tenant."""
        object_ids = (
            await self._session.scalars(
                select(ObjectORM.id).where(ObjectORM.tenant_id == tenant_id.value)
            )
        ).all()
        if object_ids:
            await self._session.execute(
                delete(FieldORM).where(FieldORM.object_id.in_(tuple(object_ids)))
            )

        await self._session.execute(
            delete(ObjectORM).where(ObjectORM.tenant_id == tenant_id.value)
        )
        await self._session.flush()

        for object_entity in objects:
            self._session.add(self._to_model(object_entity))

        await self._session.flush()

        for object_entity in objects:
            for field_entity in object_entity.fields:
                self._session.add(self._to_field_model(field_entity))

        await self._session.flush()

    async def reconcile_for_tenant(
        self,
        *,
        tenant_id: EntityIdVO,
        objects: list[ObjectEntity],
    ) -> None:
        """Синхронизирует object/field metadata tenant без полной пересоздачи.

        Метод удаляет отсутствующие объекты и поля, обновляет существующие ORM-модели
        и добавляет новые entity, чтобы сохранить id неизмененных metadata-записей.
        """
        existing_object_ids = (
            await self._session.scalars(
                select(ObjectORM.id).where(ObjectORM.tenant_id == tenant_id.value)
            )
        ).all()
        desired_object_ids = {object_entity.id.value for object_entity in objects}
        removed_object_ids = [
            object_id
            for object_id in existing_object_ids
            if object_id not in desired_object_ids
        ]
        if removed_object_ids:
            await self._session.execute(
                delete(FieldORM).where(
                    FieldORM.object_id.in_(tuple(removed_object_ids))
                )
            )
            await self._session.execute(
                delete(ObjectORM).where(ObjectORM.id.in_(tuple(removed_object_ids)))
            )

        await self._session.flush()

        for object_entity in objects:
            model = await self._session.get(ObjectORM, object_entity.id.value)
            if model is None:
                self._session.add(self._to_model(object_entity))
            else:
                self._update_object_model(model, object_entity)

        await self._session.flush()

        desired_field_ids = {
            field_entity.id.value
            for object_entity in objects
            for field_entity in object_entity.fields
        }
        if desired_object_ids:
            existing_field_ids = (
                await self._session.scalars(
                    select(FieldORM.id).where(
                        FieldORM.object_id.in_(tuple(desired_object_ids))
                    )
                )
            ).all()
            removed_field_ids = [
                field_id
                for field_id in existing_field_ids
                if field_id not in desired_field_ids
            ]
            if removed_field_ids:
                await self._session.execute(
                    delete(FieldORM).where(FieldORM.id.in_(tuple(removed_field_ids)))
                )

        for object_entity in objects:
            for field_entity in object_entity.fields:
                model = await self._session.get(FieldORM, field_entity.id.value)
                if model is None:
                    self._session.add(self._to_field_model(field_entity))
                else:
                    self._update_field_model(model, field_entity)

        await self._session.flush()

    async def _load_fields(self, object_ids: list[UUID]) -> dict[UUID, list[FieldORM]]:
        """Загружает field-модели пачкой и группирует их по object_id."""
        if not object_ids:
            return {}

        models = (
            await self._session.scalars(
                select(FieldORM)
                .where(FieldORM.object_id.in_(tuple(object_ids)))
                .order_by(FieldORM.created_at, FieldORM.id)
            )
        ).all()
        grouped: dict[UUID, list[FieldORM]] = defaultdict(list)
        for model in models:
            grouped[model.object_id].append(model)
        return grouped

    @staticmethod
    def _to_model(object_entity: ObjectEntity) -> ObjectORM:
        """Мапит доменную ObjectEntity в SQLAlchemy-модель."""
        return ObjectORM(
            id=object_entity.id.value,
            created_at=object_entity.created_at,
            updated_at=object_entity.updated_at,
            tenant_id=object_entity.tenant_id.value,
            data_source_id=object_entity.data_source_id.value,
            kind=object_entity.kind.value,
            singular_name=object_entity.object_name.singular,
            plural_name=object_entity.object_name.plural,
            singular_label=object_entity.object_label.singular,
            plural_label=object_entity.object_label.plural,
            description=object_entity.description,
        )

    @staticmethod
    def _to_field_model(field_entity: FieldEntity) -> FieldORM:
        """Мапит доменную FieldEntity в SQLAlchemy-модель."""
        return FieldORM(
            id=field_entity.id.value,
            created_at=field_entity.created_at,
            updated_at=field_entity.updated_at,
            object_id=field_entity.object_id.value,
            kind=field_entity.kind.value,
            field_name=field_entity.field_name.value,
            field_type_code=field_entity.field_type.code.value,
            label=field_entity.label.value,
            description=field_entity.description,
            is_nullable=field_entity.is_nullable,
            default_value=field_entity.default_value,
            options=field_entity.options,
            settings=field_entity.settings,
        )

    @staticmethod
    def _update_object_model(model: ObjectORM, object_entity: ObjectEntity) -> None:
        """Копирует изменяемые поля ObjectEntity в существующую ORM-модель."""
        model.tenant_id = object_entity.tenant_id.value
        model.data_source_id = object_entity.data_source_id.value
        model.kind = object_entity.kind.value
        model.singular_name = object_entity.object_name.singular
        model.plural_name = object_entity.object_name.plural
        model.singular_label = object_entity.object_label.singular
        model.plural_label = object_entity.object_label.plural
        model.description = object_entity.description
        model.updated_at = object_entity.updated_at

    @staticmethod
    def _update_field_model(model: FieldORM, field_entity: FieldEntity) -> None:
        """Копирует изменяемые поля FieldEntity в существующую ORM-модель."""
        model.object_id = field_entity.object_id.value
        model.kind = field_entity.kind.value
        model.field_name = field_entity.field_name.value
        model.field_type_code = field_entity.field_type.code.value
        model.label = field_entity.label.value
        model.description = field_entity.description
        model.is_nullable = field_entity.is_nullable
        model.default_value = field_entity.default_value
        model.options = field_entity.options
        model.settings = field_entity.settings
        model.updated_at = field_entity.updated_at

    @staticmethod
    def _map_model(model: ObjectORM, field_models: list[FieldORM]) -> ObjectEntity:
        """Мапит ORM object-модель и ее fields в доменную ObjectEntity."""
        return ObjectEntity(
            id=EntityIdVO.from_value(model.id),
            created_at=model.created_at,
            updated_at=model.updated_at,
            tenant_id=EntityIdVO.from_value(model.tenant_id),
            data_source_id=EntityIdVO.from_value(model.data_source_id),
            kind=ObjectKind(model.kind),
            object_name=ObjectNameVO(
                singular=model.singular_name,
                plural=model.plural_name,
            ),
            object_label=ObjectLabelVO(
                singular=model.singular_label,
                plural=model.plural_label,
            ),
            description=model.description,
            fields=[
                SqlAlchemyObjectRepository._map_field_model(field_model)
                for field_model in field_models
            ],
        )

    @staticmethod
    def _map_field_model(model: FieldORM) -> FieldEntity:
        """Мапит ORM field-модель в доменную FieldEntity."""
        return FieldEntity(
            id=EntityIdVO.from_value(model.id),
            created_at=model.created_at,
            updated_at=model.updated_at,
            object_id=EntityIdVO.from_value(model.object_id),
            kind=FieldKind(model.kind),
            field_name=FieldNameVO(model.field_name),
            field_type=FieldTypeVO(code=FieldTypeEnum(model.field_type_code)),
            label=FieldLabelVO(model.label),
            description=model.description,
            is_nullable=model.is_nullable,
            default_value=model.default_value,
            options=dict(model.options or {}),
            settings=dict(model.settings or {}),
        )
