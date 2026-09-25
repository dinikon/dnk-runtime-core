from datetime import datetime
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from src.modules.shared.application.persistence.tenant_schema_naming import (
    TenantSchemaNaming,
)
from src.modules.shared.infrastructure.persistence.base import TENANT_SCHEMA_ALIAS
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


class ContactPointPersistenceMappingError(RuntimeError):
    """Некорректное значение в сохранённой строке."""


def checked(value, expected, *, optional=False):
    """Проверяет примитив перед восстановлением domain model."""
    if value is None and optional:
        return None
    if not isinstance(value, expected) or (
        expected is datetime and value.tzinfo is None
    ):
        raise ContactPointPersistenceMappingError(
            "Invalid persisted contact point data."
        )
    return value


def identifier(value, cls=EntityIdVO, *, optional=False):
    """Проверяет и восстанавливает типизированный UUID."""
    if value is None and optional:
        return None
    checked(value, (UUID, str))
    return cls.from_value(value)


def audit(row, *, optional_actor=False):
    """Читает общий audit с явной проверкой типов."""
    return dict(
        created_at=checked(row["created_at"], datetime),
        updated_at=checked(row["updated_at"], datetime),
        created_by=identifier(row["created_by"], optional=optional_actor),
        updated_by=identifier(row["updated_by"], optional=optional_actor),
    )


def audit_values(entity):
    """Преобразует audit в persistence primitives."""
    return dict(
        created_at=entity.created_at,
        updated_at=entity.updated_at,
        created_by=entity.created_by.uuid if entity.created_by else None,
        updated_by=entity.updated_by.uuid if entity.updated_by else None,
    )


class ContactPointsSessionRepository:
    """Общая session без сохранения текущего tenant в repository."""

    def __init__(self, session: AsyncSession, naming: TenantSchemaNaming):
        self.session, self.naming = session, naming

    def options(self, tenant_id: EntityIdVO):
        """Ограничивает один statement tenant-схемой."""
        return {
            "schema_translate_map": {
                TENANT_SCHEMA_ALIAS: self.naming.schema_name(tenant_id)
            }
        }


__all__ = [
    "ContactPointPersistenceMappingError",
    "ContactPointsSessionRepository",
    "checked",
    "identifier",
    "audit",
    "audit_values",
]
