from sqlalchemy import insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.contact_points.domain.contact_point.value_object.value import (
    ContactPointType,
)
from src.modules.contact_points.domain.label.entity import ContactPointLabel
from src.modules.contact_points.domain.label.error import ContactPointLabelNotFoundError
from src.modules.contact_points.domain.label.value_object.identifier import (
    ContactPointLabelIdVO,
)
from src.modules.contact_points.infrastructure.persistence.base import (
    tenant_execution_options,
)
from src.modules.contact_points.infrastructure.persistence.mappers import (
    ContactPointLabelMapper,
)
from src.modules.contact_points.infrastructure.persistence.models import (
    ContactPointLabelModel,
)
from src.modules.shared.application.persistence.tenant_schema_naming import (
    TenantSchemaNaming,
)
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


class SqlAlchemyContactPointLabelRepository:
    """Запросы tenant-настроек без преобразований domain-полей."""

    def __init__(self, session: AsyncSession, naming: TenantSchemaNaming) -> None:
        self._session = session
        self._naming = naming

    async def get(
        self,
        tenant_id: EntityIdVO,
        label_id: ContactPointLabelIdVO,
        *,
        for_update: bool = False,
    ) -> ContactPointLabel:
        """Читает и при изменении блокирует настройку."""
        table = ContactPointLabelModel.__table__
        statement = (
            select(table)
            .where(table.c.id == label_id.uuid)
            .execution_options(**tenant_execution_options(self._naming, tenant_id))
        )
        if for_update:
            statement = statement.with_for_update()
        result = await self._session.execute(statement)
        row = result.mappings().one_or_none()
        if row is None:
            raise ContactPointLabelNotFoundError("Подпись не найдена.")
        return ContactPointLabelMapper.to_domain(row)

    async def list(
        self,
        tenant_id: EntityIdVO,
        point_type: ContactPointType | None = None,
        *,
        for_share: bool = False,
    ) -> tuple[ContactPointLabel, ...]:
        """Читает подписи в стабильном порядке блокировок по id."""
        table = ContactPointLabelModel.__table__
        statement = (
            select(table)
            .order_by(table.c.id)
            .execution_options(**tenant_execution_options(self._naming, tenant_id))
        )
        if point_type is not None:
            statement = statement.where(table.c.type == point_type.value)
        if for_share:
            statement = statement.with_for_update(read=True)
        result = await self._session.execute(statement)
        return tuple(
            ContactPointLabelMapper.to_domain(row) for row in result.mappings()
        )

    async def add(self, tenant_id: EntityIdVO, label: ContactPointLabel) -> None:
        """Добавляет подпись текущего пользователя."""
        statement = (
            insert(ContactPointLabelModel.__table__)
            .values(ContactPointLabelMapper.to_insert_values(label))
            .execution_options(**tenant_execution_options(self._naming, tenant_id))
        )
        await self._session.execute(statement)

    async def save(self, tenant_id: EntityIdVO, label: ContactPointLabel) -> None:
        """Сохраняет изменяемые поля из маппера."""
        table = ContactPointLabelModel.__table__
        statement = (
            update(table)
            .where(table.c.id == label.id.uuid)
            .values(ContactPointLabelMapper.to_update_values(label))
            .execution_options(**tenant_execution_options(self._naming, tenant_id))
        )
        result = await self._session.execute(statement)
        if not result.rowcount:
            raise ContactPointLabelNotFoundError("Подпись не найдена.")


__all__ = ["SqlAlchemyContactPointLabelRepository"]
