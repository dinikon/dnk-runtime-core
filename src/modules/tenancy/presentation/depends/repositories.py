from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from src.modules.tenancy.application.admin_onboarding.ports.repositories import (
    TenantDataSourceRepositoryProtocol,
    TenantDomainRepositoryProtocol,
    TenantRepositoryProtocol,
)
from src.modules.tenancy.infrastructure.repositories import (
    SqlAlchemyTenantDataSourceRepository,
    SqlAlchemyTenantDomainRepository,
    SqlAlchemyTenantRepository,
)
from src.modules.shared.depends.uow import UoWDep


def get_tenants_repository(uow: UoWDep) -> TenantRepositoryProtocol:
    return SqlAlchemyTenantRepository(uow.session)


TenantsRepositoryDep = Annotated[
    TenantRepositoryProtocol,
    Depends(get_tenants_repository),
]


def get_tenant_domains_repository(uow: UoWDep) -> TenantDomainRepositoryProtocol:
    return SqlAlchemyTenantDomainRepository(uow.session)


TenantDomainsRepositoryDep = Annotated[
    TenantDomainRepositoryProtocol,
    Depends(get_tenant_domains_repository),
]


def get_tenant_data_sources_repository(
    uow: UoWDep,
) -> TenantDataSourceRepositoryProtocol:
    return SqlAlchemyTenantDataSourceRepository(uow.session)


TenantDataSourcesRepositoryDep = Annotated[
    TenantDataSourceRepositoryProtocol,
    Depends(get_tenant_data_sources_repository),
]

__all__ = [
    "get_tenants_repository",
    "TenantsRepositoryDep",
    "get_tenant_domains_repository",
    "TenantDomainsRepositoryDep",
    "get_tenant_data_sources_repository",
    "TenantDataSourcesRepositoryDep",
]
