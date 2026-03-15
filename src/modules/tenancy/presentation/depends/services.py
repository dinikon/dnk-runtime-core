from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import Depends

from src.modules.identity.application.provisioning.services.user_service import (
    UserService,
    UserServiceProtocol,
)
from src.modules.identity.infrastructure.repositories import SqlAlchemyUserRepository
from src.modules.shared.depends.uow import UoWDep
from src.modules.tenancy.application.admin_onboarding.ports.identity import (
    IdentityProvisioningServiceProtocol,
    ProvisionedTenantAdmin,
)
from src.modules.tenancy.application.admin_onboarding.services.tenant_domain_service import (
    TenantDomainService,
    TenantDomainServiceProtocol,
)
from src.modules.tenancy.application.admin_onboarding.services.tenant_service import (
    TenantService,
    TenantServiceProtocol,
)
from src.modules.tenancy.presentation.depends.repositories import (
    TenantDomainsRepositoryDep,
    TenantsRepositoryDep,
)


class IdentityProvisioningServiceAdapter(IdentityProvisioningServiceProtocol):
    def __init__(self, user_service: UserServiceProtocol):
        self._user_service = user_service

    async def create_tenant_admin(
        self,
        tenant_id: UUID,
        first_name: str,
        last_name: str,
        email: str,
    ) -> ProvisionedTenantAdmin:
        created_admin = await self._user_service.create_tenant_admin(
            tenant_id=tenant_id,
            first_name=first_name,
            last_name=last_name,
            email=email,
        )
        return ProvisionedTenantAdmin(
            user_id=created_admin.user_id,
            user_email_id=created_admin.user_email_id,
            user_status=created_admin.user_status,
        )


def get_tenant_service(
    tenants_repository: TenantsRepositoryDep,
) -> TenantServiceProtocol:
    return TenantService(tenants_repository)


TenantServiceDep = Annotated[
    TenantServiceProtocol,
    Depends(get_tenant_service),
]


def get_tenant_domain_service(
    tenant_domains_repository: TenantDomainsRepositoryDep,
) -> TenantDomainServiceProtocol:
    return TenantDomainService(tenant_domains_repository)


TenantDomainServiceDep = Annotated[
    TenantDomainServiceProtocol,
    Depends(get_tenant_domain_service),
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
    "IdentityProvisioningServiceAdapter",
    "get_tenant_service",
    "TenantServiceDep",
    "get_tenant_domain_service",
    "TenantDomainServiceDep",
    "get_identity_provisioning_service",
    "IdentityProvisioningServiceDep",
]
