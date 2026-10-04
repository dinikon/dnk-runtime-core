from typing import Annotated

from fastapi import Depends

from src.config import dnk_config
from src.modules.tenancy.application.tenant.tenant_schema_naming import (
    TenantSchemaNaming,
)


def get_tenant_naming() -> TenantSchemaNaming:
    """Создаёт стратегию именования tenant-схем для репозиториев модуля."""
    return TenantSchemaNaming(dnk_config.SCHEMA_PREFIX)


TenantNamingDep = Annotated[TenantSchemaNaming, Depends(get_tenant_naming)]
