from sqlalchemy import delete, insert, select, tuple_
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.contact_points.domain.binding.entity import ContactPointBinding
from src.modules.contact_points.domain.binding.repository import BoundContactPoint
from src.modules.contact_points.domain.binding.value_object.target import (
    ContactPointTargetVO,
)
from src.modules.contact_points.domain.contact_point.value_object.identifier import (
    ContactPointIdVO,
)
from src.modules.contact_points.infrastructure.persistence.base import (
    tenant_execution_options,
)
from src.modules.contact_points.infrastructure.persistence.mappers import (
    ContactPointBindingMapper,
)
from src.modules.contact_points.infrastructure.persistence.models import (
    ContactPointBindingModel,
    ContactPointModel,
)
from src.modules.shared.application.persistence.tenant_schema_naming import (
    TenantSchemaNaming,
)
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


class SqlAlchemyContactPointBindingRepository:
    """Запросы связей и их projections без восстановления domain в repository."""

    def __init__(self, session: AsyncSession, naming: TenantSchemaNaming) -> None:
        self._session = session
        self._naming = naming

    async def list_for_targets(
        self, tenant_id: EntityIdVO, targets: tuple[ContactPointTargetVO, ...]
    ) -> tuple[BoundContactPoint, ...]:
        """Читает все адреса страницы одним запросом с фиксированными aliases."""
        if not targets:
            return ()
        binding = ContactPointBindingModel.__table__
        point = ContactPointModel.__table__
        statement = (
            select(
                binding.c.id,
                binding.c.contact_point_id,
                binding.c.model_key,
                binding.c.record_id,
                binding.c.label_id,
                binding.c.position,
                binding.c.created_at,
                binding.c.updated_at,
                binding.c.created_by,
                binding.c.updated_by,
                point.c.id.label("point_id"),
                point.c.type.label("point_type"),
                point.c.canonical_value.label("point_canonical_value"),
                point.c.country_code.label("point_country_code"),
                point.c.created_at.label("point_created_at"),
                point.c.updated_at.label("point_updated_at"),
                point.c.created_by.label("point_created_by"),
                point.c.updated_by.label("point_updated_by"),
            )
            .select_from(binding.join(point, binding.c.contact_point_id == point.c.id))
            .where(
                tuple_(binding.c.model_key, binding.c.record_id).in_(
                    [(target.model_key, target.record_id.uuid) for target in targets]
                )
            )
            .order_by(
                binding.c.model_key,
                binding.c.record_id,
                point.c.type,
                binding.c.position,
                binding.c.id,
            )
            .execution_options(**tenant_execution_options(self._naming, tenant_id))
        )
        result = await self._session.execute(statement)
        return tuple(
            ContactPointBindingMapper.to_bound_domain(row) for row in result.mappings()
        )

    async def list_targets(
        self, tenant_id: EntityIdVO, point_id: ContactPointIdVO
    ) -> tuple[ContactPointTargetVO, ...]:
        """Читает проекцию владельцев заданного адреса."""
        table = ContactPointBindingModel.__table__
        statement = (
            select(table.c.model_key, table.c.record_id)
            .where(table.c.contact_point_id == point_id.uuid)
            .order_by(table.c.model_key, table.c.record_id)
            .execution_options(**tenant_execution_options(self._naming, tenant_id))
        )
        result = await self._session.execute(statement)
        return tuple(
            ContactPointBindingMapper.to_target(row) for row in result.mappings()
        )

    async def remove_target(
        self, tenant_id: EntityIdVO, target: ContactPointTargetVO
    ) -> None:
        """Удаляет только связи заблокированного владельца."""
        table = ContactPointBindingModel.__table__
        statement = (
            delete(table)
            .where(
                table.c.model_key == target.model_key,
                table.c.record_id == target.record_id.uuid,
            )
            .execution_options(**tenant_execution_options(self._naming, tenant_id))
        )
        await self._session.execute(statement)

    async def replace_for_target(
        self,
        tenant_id: EntityIdVO,
        target: ContactPointTargetVO,
        bindings: tuple[ContactPointBinding, ...],
    ) -> None:
        """Атомарно заменяет строки, сохраняя id/audit; допускает обмен адресами."""
        # Owner lock serializes writers; delete+insert avoids transient unique conflicts during swaps.
        await self.remove_target(tenant_id, target)
        if not bindings:
            return
        statement = insert(ContactPointBindingModel.__table__).execution_options(
            **tenant_execution_options(self._naming, tenant_id)
        )
        values = [
            ContactPointBindingMapper.to_insert_values(binding) for binding in bindings
        ]
        await self._session.execute(statement, values)


__all__ = ["SqlAlchemyContactPointBindingRepository"]
