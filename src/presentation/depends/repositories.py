from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from src.application.admin_tenants.ports.repositories import (
    TenantDomainRepositoryProtocol,
    TenantRepositoryProtocol,
    UserRepositoryProtocol,
)
from src.infrastructure.admin_tenants.repositories import (
    SqlAlchemyTenantDomainRepository,
    SqlAlchemyTenantRepository,
    SqlAlchemyUserRepository,
)
from src.presentation.depends.uow import UoWDep


def get_tenants_repository(uow: UoWDep) -> TenantRepositoryProtocol:
    return SqlAlchemyTenantRepository(uow.session)


TenantsRepositoryDep = Annotated[
    TenantRepositoryProtocol,
    Depends(get_tenants_repository),
]


def get_users_repository(uow: UoWDep) -> UserRepositoryProtocol:
    return SqlAlchemyUserRepository(uow.session)


UsersRepositoryDep = Annotated[
    UserRepositoryProtocol,
    Depends(get_users_repository),
]


def get_tenant_domains_repository(uow: UoWDep) -> TenantDomainRepositoryProtocol:
    return SqlAlchemyTenantDomainRepository(uow.session)


TenantDomainsRepositoryDep = Annotated[
    TenantDomainRepositoryProtocol,
    Depends(get_tenant_domains_repository),
]

__all__ = [
    "get_tenants_repository",
    "TenantsRepositoryDep",
    "get_users_repository",
    "UsersRepositoryDep",
    "get_tenant_domains_repository",
    "TenantDomainsRepositoryDep",
]
