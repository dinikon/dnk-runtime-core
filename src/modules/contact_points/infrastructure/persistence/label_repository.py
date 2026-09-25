from sqlalchemy import insert, select, update
from src.modules.contact_points.domain.label.entity import ContactPointLabel
from src.modules.contact_points.domain.label.error import ContactPointLabelNotFoundError
from src.modules.contact_points.domain.label.value_object.identifier import (
    ContactPointLabelIdVO,
)
from src.modules.contact_points.domain.label.value_object.name import (
    ContactPointLabelNameVO,
)
from src.modules.contact_points.domain.contact_point.value_object.value import (
    ContactPointType,
)
from src.modules.contact_points.infrastructure.persistence.base import (
    ContactPointsSessionRepository,
    checked,
    identifier,
    audit,
    audit_values,
)
from src.modules.contact_points.infrastructure.persistence.models import (
    ContactPointLabelModel,
)


def label_entity(row):
    """Восстанавливает подпись, включая migration audit без actor."""
    return ContactPointLabel(
        id=identifier(row["id"], ContactPointLabelIdVO),
        type=ContactPointType(checked(row["type"], str)),
        name=ContactPointLabelNameVO(checked(row["name"], str)),
        is_active=checked(row["is_active"], bool),
        **audit(row, optional_actor=True),
    )


class SqlAlchemyContactPointLabelRepository(ContactPointsSessionRepository):
    """Хранит tenant-настройки подписей."""

    async def get(self, tenant_id, label_id, *, for_update=False):
        """Читает и при изменении блокирует настройку."""
        t = ContactPointLabelModel.__table__
        statement = select(t).where(t.c.id == label_id.uuid)
        if for_update:
            statement = statement.with_for_update()
        row = (
            (
                await self.session.execute(
                    statement.execution_options(**self.options(tenant_id))
                )
            )
            .mappings()
            .one_or_none()
        )
        if row is None:
            raise ContactPointLabelNotFoundError("Подпись не найдена.")
        return label_entity(row)

    async def list(self, tenant_id, point_type=None, *, for_share=False):
        """Читает настройки; shared locks согласуют назначения с archive."""
        t = ContactPointLabelModel.__table__
        statement = select(t).order_by(t.c.id)
        if point_type:
            statement = statement.where(t.c.type == point_type.value)
        if for_share:
            statement = statement.with_for_update(read=True)
        rows = (
            await self.session.execute(
                statement.execution_options(**self.options(tenant_id))
            )
        ).mappings()
        return tuple(
            sorted(
                (label_entity(row) for row in rows),
                key=lambda label: (
                    label.type,
                    label.name.value.casefold(),
                    str(label.id),
                ),
            )
        )

    async def add(self, tenant_id, label):
        """Добавляет подпись текущего пользователя."""
        await self.session.execute(
            insert(ContactPointLabelModel.__table__)
            .values(
                id=label.id.uuid,
                type=label.type.value,
                name=label.name.value,
                is_active=label.is_active,
                **audit_values(label),
            )
            .execution_options(**self.options(tenant_id))
        )

    async def save(self, tenant_id, label):
        """Сохраняет только изменяемые поля и update audit."""
        t = ContactPointLabelModel.__table__
        result = await self.session.execute(
            update(t)
            .where(t.c.id == label.id.uuid)
            .values(
                name=label.name.value,
                is_active=label.is_active,
                updated_at=label.updated_at,
                updated_by=label.updated_by.uuid,
            )
            .execution_options(**self.options(tenant_id))
        )
        if not result.rowcount:
            raise ContactPointLabelNotFoundError("Подпись не найдена.")


__all__ = ["SqlAlchemyContactPointLabelRepository", "label_entity"]
