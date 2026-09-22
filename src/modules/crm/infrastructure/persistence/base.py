from datetime import datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.shared.application.persistence.tenant_schema_naming import (
    TenantSchemaNaming,
)
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.shared.infrastructure.persistence.base import TENANT_SCHEMA_ALIAS


class CrmPersistenceMappingError(RuntimeError):
    """Сохранённое CRM-значение нарушает application-контракт."""


def checked(value, expected, *, optional: bool = False):
    """Проверяет persistence primitive до передачи в domain."""
    if optional and value is None:
        return None
    if not isinstance(value, expected):
        raise CrmPersistenceMappingError("Unexpected persisted CRM value type.")
    if expected is datetime and value.tzinfo is None:
        raise CrmPersistenceMappingError("Persisted timestamp must have timezone.")
    return value


def identifier(value, cls=EntityIdVO):
    """Преобразует UUID representation в конкретный identifier VO."""
    if not isinstance(value, (UUID, str)):
        raise CrmPersistenceMappingError("Invalid persisted CRM identifier.")
    return cls.from_value(value)


class CrmSessionRepository:
    """Общий tenant scope CRM repositories без сохранения tenant в instance."""

    def __init__(self, session: AsyncSession, naming: TenantSchemaNaming):
        self.session = session
        self.naming = naming

    def execution_options(self, tenant_id: EntityIdVO) -> dict[str, object]:
        """Возвращает schema translation для текущего вызова repository."""
        return {
            "schema_translate_map": {
                TENANT_SCHEMA_ALIAS: self.naming.schema_name(tenant_id)
            }
        }


__all__ = [
    "CrmPersistenceMappingError",
    "CrmSessionRepository",
    "checked",
    "identifier",
]
