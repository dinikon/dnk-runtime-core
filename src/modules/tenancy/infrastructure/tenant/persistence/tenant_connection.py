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
