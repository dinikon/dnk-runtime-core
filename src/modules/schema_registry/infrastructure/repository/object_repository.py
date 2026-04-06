from __future__ import annotations

from collections import defaultdict

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.shared import EntityIdVO
from src.modules.schema_registry.domain.field.entity import FieldEntity
from src.modules.schema_registry.domain.field.enum.field_type import FieldTypeEnum
from src.modules.schema_registry.domain.field.enum.field_type_mode import (
    FieldTypeModeEnum,
)
from src.modules.schema_registry.domain.field.enum.sql_type_preset import (
    SqlTypePresetEnum,
)
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
from src.modules.schema_registry.domain.object.value_object.object_name import (
    ObjectNameVO,
)
from src.modules.schema_registry.infrastructure.persistence.field import FieldORM
from src.modules.schema_registry.infrastructure.persistence.object import ObjectORM


class SqlAlchemyObjectRepository(ObjectRepositoryProtocol):
    def __init__(self, session: AsyncSession):
        self._session = session

    async def get_by_tenant_and_plural_name(
        self,
        tenant_id: EntityIdVO,
        plural_name: str,
    ) -> ObjectEntity | None:
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

    async def get_by_id(self, object_id: EntityIdVO) -> ObjectEntity | None:
        model = await self._session.get(ObjectORM, object_id.value)
        if model is None:
            return None

        field_models = await self._load_fields([model.id])
        return self._map_model(model, field_models.get(model.id, []))

    async def save(self, object_entity: ObjectEntity) -> None:
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

    async def _load_fields(
        self, object_ids: list[object]
    ) -> dict[object, list[FieldORM]]:
        if not object_ids:
            return {}

        models = (
            await self._session.scalars(
                select(FieldORM)
                .where(FieldORM.object_id.in_(tuple(object_ids)))
                .order_by(FieldORM.created_at, FieldORM.id)
            )
        ).all()
        grouped: dict[object, list[FieldORM]] = defaultdict(list)
        for model in models:
            grouped[model.object_id].append(model)
        return grouped

    @staticmethod
    def _to_model(object_entity: ObjectEntity) -> ObjectORM:
        return ObjectORM(
            id=object_entity.id.value,
            created_at=object_entity.created_at,
            updated_at=object_entity.updated_at,
            tenant_id=object_entity.tenant_id.value,
            data_source_id=object_entity.data_source_id.value,
            singular_name=object_entity.object_name.singular,
            plural_name=object_entity.object_name.plural,
            singular_label=object_entity.object_label.singular,
            plural_label=object_entity.object_label.plural,
            description=object_entity.description,
        )

    @staticmethod
    def _to_field_model(field_entity: FieldEntity) -> FieldORM:
        return FieldORM(
            id=field_entity.id.value,
            created_at=field_entity.created_at,
            updated_at=field_entity.updated_at,
            object_id=field_entity.object_id.value,
            field_name=field_entity.field_name.value,
            field_type_code=field_entity.field_type.code.value,
            field_type_mode=field_entity.field_type.mode.value,
            field_type_literal_value=field_entity.field_type.literal_value,
            field_type_sql_preset=(
                field_entity.field_type.sql_preset.value
                if field_entity.field_type.sql_preset is not None
                else None
            ),
            label=field_entity.label.value,
            description=field_entity.description,
            is_nullable=field_entity.is_nullable,
            default_value=field_entity.default_value,
            options=field_entity.options,
            settings=field_entity.settings,
        )

    @staticmethod
    def _map_model(model: ObjectORM, field_models: list[FieldORM]) -> ObjectEntity:
        return ObjectEntity(
            id=EntityIdVO.from_value(model.id),
            created_at=model.created_at,
            updated_at=model.updated_at,
            tenant_id=EntityIdVO.from_value(model.tenant_id),
            data_source_id=EntityIdVO.from_value(model.data_source_id),
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
        return FieldEntity(
            id=EntityIdVO.from_value(model.id),
            created_at=model.created_at,
            updated_at=model.updated_at,
            object_id=EntityIdVO.from_value(model.object_id),
            field_name=FieldNameVO(model.field_name),
            field_type=FieldTypeVO(
                code=FieldTypeEnum(model.field_type_code),
                mode=FieldTypeModeEnum(model.field_type_mode),
                literal_value=model.field_type_literal_value,
                sql_preset=(
                    SqlTypePresetEnum(model.field_type_sql_preset)
                    if model.field_type_sql_preset is not None
                    else None
                ),
            ),
            label=FieldLabelVO(model.label),
            description=model.description,
            is_nullable=model.is_nullable,
            default_value=model.default_value,
            options=dict(model.options or {}),
            settings=dict(model.settings or {}),
        )
