from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from src.modules.identity.application.provisioning.services.user_service import (
    UserService,
)
from src.modules.identity.infrastructure.repositories import SqlAlchemyUserRepository
from src.modules.shared.depends.uow import UoWDep
from src.modules.tenancy.application.ports.identity import (
    IdentityProvisioningServiceProtocol,
)
from src.modules.tenancy.domain.repositories import (
    TenantDomainRepositoryProtocol,
    TenantRepositoryProtocol,
)
from src.modules.tenancy.infrastructure.identity_provisioning import (
    IdentityProvisioningServiceAdapter,
)
from src.modules.tenancy.infrastructure.repositories import (
    SqlAlchemyTenantDomainRepository,
    SqlAlchemyTenantRepository,
)


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


def get_identity_provisioning_service(
    uow: UoWDep,
) -> IdentityProvisioningServiceProtocol:
    user_service = UserService(SqlAlchemyUserRepository(uow.session))
    return IdentityProvisioningServiceAdapter(user_service)


IdentityProvisioningServiceDep = Annotated[
    IdentityProvisioningServiceProtocol,
    Depends(get_identity_provisioning_service),
]


__all__ = [
    "IdentityProvisioningServiceDep",
    "TenantDomainsRepositoryDep",
    "TenantsRepositoryDep",
    "get_identity_provisioning_service",
    "get_tenant_domains_repository",
    "get_tenants_repository",
]
