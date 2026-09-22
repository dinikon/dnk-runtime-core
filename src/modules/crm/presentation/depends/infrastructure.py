from typing import Annotated

from fastapi import Depends

from src.config import dnk_config
from src.modules.crm.infrastructure.persistence import (
    SqlAlchemyCompanyRepository,
    SqlAlchemyContactRepository,
)
from src.modules.shared.application.persistence.tenant_schema_naming import (
    TenantSchemaNaming,
)
from src.modules.shared.presentation.persistence.depends import UoWDep


def get_tenant_naming() -> TenantSchemaNaming:
    """Возвращает общую стратегию именования tenant-схем."""
    return TenantSchemaNaming(dnk_config.SCHEMA_PREFIX)


TenantNamingDep = Annotated[TenantSchemaNaming, Depends(get_tenant_naming)]


def get_contact_repository(uow: UoWDep, naming: TenantNamingDep):
    """Создаёт contact repository на текущей UoW session."""
    return SqlAlchemyContactRepository(uow.session, naming)


ContactRepositoryDep = Annotated[
    SqlAlchemyContactRepository, Depends(get_contact_repository)
]


def get_company_repository(uow: UoWDep, naming: TenantNamingDep):
    """Создаёт company repository на текущей UoW session."""
    return SqlAlchemyCompanyRepository(uow.session, naming)


CompanyRepositoryDep = Annotated[
    SqlAlchemyCompanyRepository, Depends(get_company_repository)
]


__all__ = [
    "CompanyRepositoryDep",
    "ContactRepositoryDep",
    "TenantNamingDep",
    "get_company_repository",
    "get_contact_repository",
    "get_tenant_naming",
]
