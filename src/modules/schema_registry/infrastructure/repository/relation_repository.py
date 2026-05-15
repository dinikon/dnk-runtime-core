from __future__ import annotations

from sqlalchemy import delete, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.schema_registry.domain.datasource.value_object import DataSourceIdVO
from src.modules.schema_registry.domain.field.value_object import RuntimeFieldIdVO
from src.modules.schema_registry.domain.object.value_object import RuntimeObjectIdVO
from src.modules.schema_registry.domain.relation.entity import RelationEntity
from src.modules.schema_registry.domain.relation.repository import (
    RelationRepositoryProtocol,
)
from src.modules.schema_registry.domain.relation.value_object import RuntimeRelationIdVO
from src.modules.schema_registry.domain.seed.relation_type import RelationTypeEnum
from src.modules.schema_registry.infrastructure.persistence.relation import RelationORM
from src.modules.shared import EntityIdVO


class SqlAlchemyRelationRepository(RelationRepositoryProtocol):
    """SQLAlchemy-репозиторий runtime relation metadata."""

    def __init__(self, session: AsyncSession) -> None:
        """Инициализирует репозиторий текущей async-сессией."""
        self._session = session

    async def get_by_id(
        self,
        *,
        relation_id: RuntimeRelationIdVO,
    ) -> RelationEntity | None:
        """Ищет relation metadata по id."""
        model = await self._session.get(RelationORM, relation_id.uuid)
        if model is None:
            return None
        return self._map_model(model)

    async def list_by_tenant_id(
        self,
        *,
        tenant_id: EntityIdVO,
    ) -> list[RelationEntity]:
        """Возвращает relation metadata tenant в стабильном порядке."""
        models = (
            await self._session.scalars(
                select(RelationORM)
                .where(RelationORM.tenant_id == tenant_id.uuid)
                .order_by(RelationORM.created_at, RelationORM.id)
            )
        ).all()
        return [self._map_model(model) for model in models]

    async def list_by_object_id(
        self,
        *,
        tenant_id: EntityIdVO,
        object_id: RuntimeObjectIdVO,
    ) -> list[RelationEntity]:
        """Возвращает relations tenant, где object участвует как source или target."""
        models = (
            await self._session.scalars(
                select(RelationORM)
                .where(RelationORM.tenant_id == tenant_id.uuid)
                .where(
                    or_(
                        RelationORM.source_object_id == object_id.uuid,
                        RelationORM.target_object_id == object_id.uuid,
                    )
                )
                .order_by(RelationORM.created_at, RelationORM.id)
            )
        ).all()
        return [self._map_model(model) for model in models]

    async def get_by_tenant_and_name(
        self,
        *,
        tenant_id: EntityIdVO,
        name: str,
    ) -> RelationEntity | None:
        """Ищет relation metadata по tenant/name."""
        model = await self._session.scalar(
            select(RelationORM)
            .where(RelationORM.tenant_id == tenant_id.uuid)
            .where(RelationORM.name == name.strip())
            .limit(1)
        )
        if model is None:
            return None
        return self._map_model(model)

    async def add(self, relation: RelationEntity) -> None:
        """Добавляет одну relation metadata."""
        self._session.add(self._to_model(relation))
        await self._session.flush()

    async def delete(
        self,
        *,
        tenant_id: EntityIdVO,
        relation_id: RuntimeRelationIdVO,
    ) -> None:
        """Удаляет одну relation metadata по tenant/id."""
        await self._session.execute(
            delete(RelationORM)
            .where(RelationORM.tenant_id == tenant_id.uuid)
            .where(RelationORM.id == relation_id.uuid)
        )
        await self._session.flush()

    async def replace_all_for_tenant(
        self,
        *,
        tenant_id: EntityIdVO,
        relations: list[RelationEntity],
    ) -> None:
        """Полностью заменяет relation metadata tenant."""
        await self.clear_for_tenant(tenant_id=tenant_id)
        for relation in relations:
            self._session.add(self._to_model(relation))
        await self._session.flush()

    async def clear_for_tenant(
        self,
        *,
        tenant_id: EntityIdVO,
    ) -> None:
        """Удаляет всю relation metadata tenant."""
        await self._session.execute(
            delete(RelationORM).where(RelationORM.tenant_id == tenant_id.uuid)
        )
        await self._session.flush()

    async def reconcile_for_tenant(
        self,
        *,
        tenant_id: EntityIdVO,
        relations: list[RelationEntity],
    ) -> None:
        """Синхронизирует relation metadata tenant без удаления сохраненных строк."""
        relation_ids = [relation.id.uuid for relation in relations]
        delete_query = delete(RelationORM).where(
            RelationORM.tenant_id == tenant_id.uuid
        )
        if relation_ids:
            delete_query = delete_query.where(RelationORM.id.notin_(relation_ids))
        await self._session.execute(delete_query)
        for relation in relations:
            await self._session.merge(self._to_model(relation))
        await self._session.flush()

    @staticmethod
    def _to_model(relation: RelationEntity) -> RelationORM:
        """Мапит доменную RelationEntity в SQLAlchemy-модель."""
        return RelationORM(
            id=relation.id.uuid,
            created_at=relation.created_at,
            updated_at=relation.updated_at,
            tenant_id=relation.tenant_id.uuid,
            data_source_id=relation.data_source_id.uuid,
            name=relation.name,
            label=relation.label,
            relation_type=relation.relation_type.value,
            source_object_id=relation.source_object_id.uuid,
            target_object_id=relation.target_object_id.uuid,
            owning_object_id=(
                relation.owning_object_id.uuid
                if relation.owning_object_id is not None
                else None
            ),
            fk_field_id=(
                relation.fk_field_id.uuid if relation.fk_field_id is not None else None
            ),
            referenced_object_id=(
                relation.referenced_object_id.uuid
                if relation.referenced_object_id is not None
                else None
            ),
            referenced_field_id=(
                relation.referenced_field_id.uuid
                if relation.referenced_field_id is not None
                else None
            ),
            source_relation_name=relation.source_relation_name,
            target_relation_name=relation.target_relation_name,
            relation_table_name=relation.relation_table_name,
            source_join_column_name=relation.source_join_column_name,
            target_join_column_name=relation.target_join_column_name,
            on_delete=relation.on_delete,
            is_required=relation.is_required,
            is_unique=relation.is_unique,
            kind=relation.kind,
            settings=relation.settings,
        )

    @staticmethod
    def _map_model(model: RelationORM) -> RelationEntity:
        """Мапит ORM relation-модель в доменную RelationEntity."""
        return RelationEntity(
            id=RuntimeRelationIdVO.from_value(model.id),
            created_at=model.created_at,
            updated_at=model.updated_at,
            tenant_id=EntityIdVO.from_value(model.tenant_id),
            data_source_id=DataSourceIdVO.from_value(model.data_source_id),
            name=model.name,
            label=model.label,
            relation_type=RelationTypeEnum(model.relation_type),
            source_object_id=RuntimeObjectIdVO.from_value(model.source_object_id),
            target_object_id=RuntimeObjectIdVO.from_value(model.target_object_id),
            owning_object_id=(
                RuntimeObjectIdVO.from_value(model.owning_object_id)
                if model.owning_object_id is not None
                else None
            ),
            fk_field_id=(
                RuntimeFieldIdVO.from_value(model.fk_field_id)
                if model.fk_field_id is not None
                else None
            ),
            referenced_object_id=(
                RuntimeObjectIdVO.from_value(model.referenced_object_id)
                if model.referenced_object_id is not None
                else None
            ),
            referenced_field_id=(
                RuntimeFieldIdVO.from_value(model.referenced_field_id)
                if model.referenced_field_id is not None
                else None
            ),
            source_relation_name=model.source_relation_name,
            target_relation_name=model.target_relation_name,
            relation_table_name=model.relation_table_name,
            source_join_column_name=model.source_join_column_name,
            target_join_column_name=model.target_join_column_name,
            on_delete=model.on_delete,
            is_required=model.is_required,
            is_unique=model.is_unique,
            kind=model.kind,
            settings=dict(model.settings or {}),
        )
