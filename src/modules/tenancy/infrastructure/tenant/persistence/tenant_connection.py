"""Привязка tenant-схемы к соединению до создания сессии UoW."""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncConnection

from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.tenancy.application.tenant.tenant_schema_naming import (
    TenantSchemaNaming,
)
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_base import (
    TENANT_SCHEMA_ALIAS,
)


async def bind_tenant_schema(
    connection: AsyncConnection, tenant_id: UUID, naming: TenantSchemaNaming
) -> None:
    """Настраивает подстановку схемы для всех tenant-моделей на соединении."""
    await connection.execution_options(
        schema_translate_map={
            TENANT_SCHEMA_ALIAS: naming.schema_name(EntityIdVO.from_value(tenant_id))
        }
    )


def is_tenant_schema_bound(
    connection: AsyncConnection, tenant_id: UUID, naming: TenantSchemaNaming
) -> bool:
    """Проверяет совпадение tenant со схемой уже открытого соединения."""
    expected = naming.schema_name(EntityIdVO.from_value(tenant_id))
    options = connection.sync_connection.get_execution_options()
    return options.get("schema_translate_map", {}).get(TENANT_SCHEMA_ALIAS) == expected


async def require_tenant_schema(
    connection: AsyncConnection, tenant_id: UUID, naming: TenantSchemaNaming
) -> None:
    """Требует совпадения tenant со схемой уже открытого соединения."""
    if not is_tenant_schema_bound(connection, tenant_id, naming):
        raise RuntimeError("Tenant connection is not bound to the requested schema.")
