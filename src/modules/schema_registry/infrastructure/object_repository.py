from __future__ import annotations

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.schema_registry.domain.object.entity import ObjectEntity
from src.modules.schema_registry.domain.object.value_object.object_label import (
    ObjectLabelVO,
)
from src.modules.schema_registry.domain.object.value_object.object_name import (
    ObjectNameVO,
)
from src.modules.schema_registry.infrastructure.persistence.object import ObjectORM
from src.modules.shared import EntityIdVO


class ObjectRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def get_by_id(self, object_id: EntityIdVO) -> ObjectEntity | None:
        model = await self._session.scalar(
            select(ObjectORM).where(ObjectORM.id == object_id.value).limit(1)
        )
        if model is None:
            return None
        return self._map_model(model)

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
        return self._map_model(model)

    async def save(self, object_entity: ObjectEntity) -> None:
        model = await self._session.get(ObjectORM, object_entity.id.value)
        if model is None:
            model = ObjectORM(
                id=object_entity.id.value,
                created_at=object_entity.created_at,
                updated_at=object_entity.updated_at,
                tenant_id=object_entity.tenant_id.value,
                singular_name=object_entity.object_name.singular,
                plural_name=object_entity.object_name.plural,
                singular_label=object_entity.object_label.singular,
                plural_label=object_entity.object_label.plural,
                description=object_entity.description,
            )
            self._session.add(model)
        else:
            model.tenant_id = object_entity.tenant_id.value
            model.singular_name = object_entity.object_name.singular
            model.plural_name = object_entity.object_name.plural
            model.singular_label = object_entity.object_label.singular
            model.plural_label = object_entity.object_label.plural
            model.description = object_entity.description
            model.updated_at = object_entity.updated_at

        await self._session.flush()

    async def delete(self, object_id: EntityIdVO) -> None:
        await self._session.execute(
            delete(ObjectORM).where(ObjectORM.id == object_id.value)
        )
        await self._session.flush()

    @staticmethod
    def _map_model(model: ObjectORM) -> ObjectEntity:
        return ObjectEntity(
            id=EntityIdVO.from_value(model.id),
            created_at=model.created_at,
            updated_at=model.updated_at,
            tenant_id=EntityIdVO.from_value(model.tenant_id),
            object_name=ObjectNameVO(
                singular=model.singular_name,
                plural=model.plural_name,
            ),
            object_label=ObjectLabelVO(
                singular=model.singular_label,
                plural=model.plural_label,
            ),
            description=model.description,
            fields=[],
        )
