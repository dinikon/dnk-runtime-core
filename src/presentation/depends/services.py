from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from src.application.admin_tenants.services.tenant_domain_service import (
    TenantDomainService,
    TenantDomainServiceProtocol,
)
from src.application.admin_tenants.services.tenant_service import (
    TenantService,
    TenantServiceProtocol,
)
from src.application.admin_tenants.services.user_service import (
    UserService,
    UserServiceProtocol,
)
from src.presentation.depends.repositories import (
    TenantDomainsRepositoryDep,
    TenantsRepositoryDep,
    UsersRepositoryDep,
)


def get_tenant_service(
    tenants_repository: TenantsRepositoryDep,
) -> TenantServiceProtocol:
    return TenantService(tenants_repository)


TenantServiceDep = Annotated[
    TenantServiceProtocol,
    Depends(get_tenant_service),
]


def get_user_service(users_repository: UsersRepositoryDep) -> UserServiceProtocol:
    return UserService(users_repository)


UserServiceDep = Annotated[UserServiceProtocol, Depends(get_user_service)]


def get_tenant_domain_service(
    tenant_domains_repository: TenantDomainsRepositoryDep,
) -> TenantDomainServiceProtocol:
    return TenantDomainService(tenant_domains_repository)


TenantDomainServiceDep = Annotated[
    TenantDomainServiceProtocol,
    Depends(get_tenant_domain_service),
]

__all__ = [
    "get_tenant_service",
    "TenantServiceDep",
    "get_user_service",
    "UserServiceDep",
    "get_tenant_domain_service",
    "TenantDomainServiceDep",
]
