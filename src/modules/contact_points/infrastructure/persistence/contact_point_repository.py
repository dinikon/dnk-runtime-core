from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
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
    ContactPointsSessionRepository,
    checked,
    identifier,
    audit,
    audit_values,
)
from src.modules.contact_points.infrastructure.persistence.models import (
    ContactPointModel,
)


def point_entity(row):
    """Восстанавливает неизменяемую domain-точку."""
    return ContactPoint(
        id=identifier(row["id"], ContactPointIdVO),
        type=ContactPointType(checked(row["type"], str)),
        canonical_value=ContactPointValueVO(checked(row["canonical_value"], str)),
        country_code=checked(row["country_code"], str, optional=True),
        **audit(row),
    )


class SqlAlchemyContactPointRepository(ContactPointsSessionRepository):
    """Разрешает одинаковые адреса через PostgreSQL unique constraint."""

    async def get(self, tenant_id, point_id):
        """Читает точку в заданной схеме."""
        t = ContactPointModel.__table__
        row = (
            (
                await self.session.execute(
                    select(t)
                    .where(t.c.id == point_id.uuid)
                    .execution_options(**self.options(tenant_id))
                )
            )
            .mappings()
            .one_or_none()
        )
        if row is None:
            raise ContactPointNotFoundError("Точка контакта не найдена.")
        return point_entity(row)

    async def find_by_canonical(self, tenant_id, point_type, value):
        """Ищет точку без создания."""
        t = ContactPointModel.__table__
        row = (
            (
                await self.session.execute(
                    select(t)
                    .where(
                        t.c.type == point_type.value, t.c.canonical_value == value.value
                    )
                    .execution_options(**self.options(tenant_id))
                )
            )
            .mappings()
            .one_or_none()
        )
        return point_entity(row) if row else None

    async def get_or_create(self, tenant_id, candidate):
        """Возвращает победившую вставку без rollback внешней транзакции."""
        t = ContactPointModel.__table__
        statement = (
            insert(t)
            .values(
                id=candidate.id.uuid,
                type=candidate.type.value,
                canonical_value=candidate.canonical_value.value,
                country_code=candidate.country_code,
                **audit_values(candidate),
            )
            .on_conflict_do_nothing(index_elements=[t.c.type, t.c.canonical_value])
            .returning(*t.c)
        )
        row = (
            (
                await self.session.execute(
                    statement.execution_options(**self.options(tenant_id))
                )
            )
            .mappings()
            .one_or_none()
        )
        if row:
            return point_entity(row)
        existing = await self.find_by_canonical(
            tenant_id, candidate.type, candidate.canonical_value
        )
        if existing is None:
            raise ContactPointNotFoundError(
                "Конкурентная точка недоступна; повторите запрос."
            )
        return existing


__all__ = ["SqlAlchemyContactPointRepository", "point_entity"]
