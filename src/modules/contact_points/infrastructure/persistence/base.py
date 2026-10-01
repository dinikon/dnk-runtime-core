from src.modules.tenancy.application.tenant.tenant_schema_naming import (
    TenantSchemaNaming,
)
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_base import (
    TENANT_SCHEMA_ALIAS,
)


class ContactPointPersistenceMappingError(RuntimeError):
    """Сохранённая строка не может быть восстановлена в domain model."""


def tenant_execution_options(
    naming: TenantSchemaNaming, tenant_id: EntityIdVO
) -> dict[str, dict[str, str]]:
    """Выбирает tenant-схему только для текущего statement."""
    return {
        "schema_translate_map": {TENANT_SCHEMA_ALIAS: naming.schema_name(tenant_id)}
    }


__all__ = ["ContactPointPersistenceMappingError", "tenant_execution_options"]
