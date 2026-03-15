from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from src.modules.tenancy.application.admin_onboarding.use_cases.create_tenant import (
    CreateTenantUseCase,
)
from src.modules.tenancy.application.request_context_by_host.use_case import (
    ResolveTenantRequestContextByHostUseCase,
)
from src.modules.tenancy.application.resolve_tenant_by_host.use_case import (
    ResolveTenantByHostUseCase,
)
from src.modules.tenancy.presentation.depends.repositories import (
    TenantDomainsRepositoryDep,
    TenantsRepositoryDep,
)
from src.modules.tenancy.presentation.depends.services import (
    IdentityProvisioningServiceDep,
    TenantDomainServiceDep,
    TenantServiceDep,
)
from src.modules.shared.depends.uow import UoWDep


def get_create_tenant_use_case(
    uow: UoWDep,
    tenant_service: TenantServiceDep,
    identity_provisioning_service: IdentityProvisioningServiceDep,
    tenant_domain_service: TenantDomainServiceDep,
) -> CreateTenantUseCase:
    return CreateTenantUseCase(
        uow=uow,
        tenant_service=tenant_service,
        identity_provisioning_service=identity_provisioning_service,
        tenant_domain_service=tenant_domain_service,
    )


CreateTenantUseCaseDep = Annotated[
    CreateTenantUseCase,
    Depends(get_create_tenant_use_case),
]


def get_resolve_tenant_by_host_use_case(
    tenants_repository: TenantsRepositoryDep,
    tenant_domains_repository: TenantDomainsRepositoryDep,
) -> ResolveTenantByHostUseCase:
    return ResolveTenantByHostUseCase(
        tenants_repository=tenants_repository,
        tenant_domains_repository=tenant_domains_repository,
    )


ResolveTenantByHostUseCaseDep = Annotated[
    ResolveTenantByHostUseCase,
    Depends(get_resolve_tenant_by_host_use_case),
]


def get_tenant_request_context_by_host_use_case(
    tenants_repository: TenantsRepositoryDep,
    tenant_domains_repository: TenantDomainsRepositoryDep,
) -> ResolveTenantRequestContextByHostUseCase:
    return ResolveTenantRequestContextByHostUseCase(
        tenants_repository=tenants_repository,
        tenant_domains_repository=tenant_domains_repository,
    )


TenantRequestContextByHostUseCaseDep = Annotated[
    ResolveTenantRequestContextByHostUseCase,
    Depends(get_tenant_request_context_by_host_use_case),
]

__all__ = [
    "get_create_tenant_use_case",
    "CreateTenantUseCaseDep",
    "get_resolve_tenant_by_host_use_case",
    "ResolveTenantByHostUseCaseDep",
    "get_tenant_request_context_by_host_use_case",
    "TenantRequestContextByHostUseCaseDep",
]
