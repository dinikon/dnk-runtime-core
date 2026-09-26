from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.contact_points.domain.contact_point.entity import ContactPoint
from src.modules.contact_points.domain.contact_point.error import (
    ContactPointNotFoundError,
)
from src.modules.contact_points.domain.contact_point.value_object.identifier import (
    ContactPointIdVO,
)
from src.modules.contact_points.domain.contact_point.value_object.value import (
    ContactPointType,
    ContactPointValueVO,
)
from src.modules.contact_points.infrastructure.persistence.base import (
    tenant_execution_options,
)
from src.modules.contact_points.infrastructure.persistence.mappers import (
    ContactPointMapper,
)
from src.modules.contact_points.infrastructure.persistence.models import (
    ContactPointModel,
)
from src.modules.shared.application.persistence.tenant_schema_naming import (
    TenantSchemaNaming,
)
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


class SqlAlchemyContactPointRepository:
    """Запросы tenant-справочника; восстановление domain делегируется мапперу."""

    def __init__(self, session: AsyncSession, naming: TenantSchemaNaming) -> None:
        self._session = session
        self._naming = naming

    async def get(
        self, tenant_id: EntityIdVO, point_id: ContactPointIdVO
    ) -> ContactPoint:
        """Читает точку в заданной схеме или поднимает NotFound."""
        table = ContactPointModel.__table__
        statement = (
            select(table)
            .where(table.c.id == point_id.uuid)
            .execution_options(**tenant_execution_options(self._naming, tenant_id))
        )
        result = await self._session.execute(statement)
        row = result.mappings().one_or_none()
        if row is None:
            raise ContactPointNotFoundError("Точка контакта не найдена.")
        return ContactPointMapper.to_domain(row)

    async def find_by_canonical(
        self,
        tenant_id: EntityIdVO,
        point_type: ContactPointType,
        value: ContactPointValueVO,
    ) -> ContactPoint | None:
        """Ищет точку без создания."""
        table = ContactPointModel.__table__
        statement = (
            select(table)
            .where(
                table.c.type == point_type.value, table.c.canonical_value == value.value
            )
            .execution_options(**tenant_execution_options(self._naming, tenant_id))
        )
        result = await self._session.execute(statement)
        row = result.mappings().one_or_none()
        if row is None:
            return None
        return ContactPointMapper.to_domain(row)

    async def get_or_create(
        self, tenant_id: EntityIdVO, candidate: ContactPoint
    ) -> ContactPoint:
        """Возвращает победившую вставку без rollback внешней транзакции."""
        table = ContactPointModel.__table__
        statement = (
            insert(table)
            .values(ContactPointMapper.to_insert_values(candidate))
            .on_conflict_do_nothing(constraint="uq_contact_points_value")
            .returning(table)
            .execution_options(**tenant_execution_options(self._naming, tenant_id))
        )
        result = await self._session.execute(statement)
        row = result.mappings().one_or_none()
        if row is not None:
            return ContactPointMapper.to_domain(row)
        existing = await self.find_by_canonical(
            tenant_id=tenant_id,
            point_type=candidate.type,
            value=candidate.canonical_value,
        )
        if existing is None:
            raise ContactPointNotFoundError(
                "Конкурентная точка недоступна; повторите запрос."
            )
        return existing


__all__ = ["SqlAlchemyContactPointRepository"]
