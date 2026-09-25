from sqlalchemy import delete, insert, select, tuple_
from src.modules.contact_points.domain.binding.entity import ContactPointBinding
from src.modules.contact_points.domain.binding.repository import BoundContactPoint
from src.modules.contact_points.domain.binding.value_object.identifier import (
    ContactPointBindingIdVO,
)
from src.modules.contact_points.domain.binding.value_object.target import (
    ContactPointTargetVO,
)
from src.modules.contact_points.domain.contact_point.value_object.identifier import (
    ContactPointIdVO,
)
from src.modules.contact_points.domain.label.value_object.identifier import (
    ContactPointLabelIdVO,
)
from src.modules.contact_points.infrastructure.persistence.base import (
    ContactPointsSessionRepository,
    checked,
    identifier,
    audit,
    audit_values,
)
from src.modules.contact_points.infrastructure.persistence.contact_point_repository import (
    point_entity,
)
from src.modules.contact_points.infrastructure.persistence.models import (
    ContactPointBindingModel,
    ContactPointModel,
)


def binding_entity(row):
    """Явно восстанавливает полиморфную связь."""
    return ContactPointBinding(
        id=identifier(row["id"], ContactPointBindingIdVO),
        contact_point_id=identifier(row["contact_point_id"], ContactPointIdVO),
        target=ContactPointTargetVO(
            checked(row["model_key"], str), identifier(row["record_id"])
        ),
        label_id=identifier(row["label_id"], ContactPointLabelIdVO, optional=True),
        position=checked(row["position"], int),
        **audit(row),
    )


class SqlAlchemyContactPointBindingRepository(ContactPointsSessionRepository):
    """Хранит и читает связи независимо от CRM persistence."""

    async def list_for_targets(self, tenant_id, targets):
        """Читает все адреса страницы одним запросом."""
        if not targets:
            return ()
        b, p = ContactPointBindingModel.__table__, ContactPointModel.__table__
        statement = (
            select(*b.c, *(column.label("point_" + column.name) for column in p.c))
            .select_from(b.join(p, b.c.contact_point_id == p.c.id))
            .where(
                tuple_(b.c.model_key, b.c.record_id).in_(
                    [(target.model_key, target.record_id.uuid) for target in targets]
                )
            )
            .order_by(b.c.model_key, b.c.record_id, p.c.type, b.c.position, b.c.id)
        )
        rows = (
            await self.session.execute(
                statement.execution_options(**self.options(tenant_id))
            )
        ).mappings()
        return tuple(
            BoundContactPoint(
                binding_entity(row),
                point_entity(
                    {column.name: row["point_" + column.name] for column in p.c}
                ),
            )
            for row in rows
        )

    async def list_targets(self, tenant_id, point_id):
        """Возвращает ссылки на владельцев заданного адреса."""
        t = ContactPointBindingModel.__table__
        rows = (
            await self.session.execute(
                select(t.c.model_key, t.c.record_id)
                .where(t.c.contact_point_id == point_id.uuid)
                .order_by(t.c.model_key, t.c.record_id)
                .execution_options(**self.options(tenant_id))
            )
        ).mappings()
        return tuple(
            ContactPointTargetVO(
                checked(row["model_key"], str), identifier(row["record_id"])
            )
            for row in rows
        )

    async def remove_target(self, tenant_id, target):
        """Удаляет только связи заблокированного владельца."""
        t = ContactPointBindingModel.__table__
        await self.session.execute(
            delete(t)
            .where(
                t.c.model_key == target.model_key,
                t.c.record_id == target.record_id.uuid,
            )
            .execution_options(**self.options(tenant_id))
        )

    async def replace_for_target(self, tenant_id, target, bindings):
        """Атомарно заменяет строки, сохраняя id/audit; допускает обмен адресами."""
        # Delete+insert avoids transient unique conflicts during rebind swaps. The owner lock
        # serializes writers; no intermediate state escapes the caller's transaction.
        await self.remove_target(tenant_id, target)
        if bindings:
            values = [
                dict(
                    id=b.id.uuid,
                    contact_point_id=b.contact_point_id.uuid,
                    model_key=target.model_key,
                    record_id=target.record_id.uuid,
                    label_id=b.label_id.uuid if b.label_id else None,
                    position=b.position,
                    **audit_values(b),
                )
                for b in bindings
            ]
            await self.session.execute(
                insert(ContactPointBindingModel.__table__).execution_options(
                    **self.options(tenant_id)
                ),
                values,
            )


__all__ = ["SqlAlchemyContactPointBindingRepository", "binding_entity"]
