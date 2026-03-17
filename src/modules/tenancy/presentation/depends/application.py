from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from src.modules.shared.depends.uow import UoWDep
from src.modules.tenancy.application.use_cases import (
    CreateTenantUseCase,
    ResolveTenantByHostUseCase,
    ResolveTenantRequestContextByHostUseCase,
)
from src.modules.tenancy.presentation.depends.infrastructure import (
    IdentityProvisioningServiceDep,
    RuntimeSchemaBootstrapperDep,
    TenantDomainsRepositoryDep,
    TenantsRepositoryDep,
)


def get_create_tenant_use_case(
    uow: UoWDep,
    tenants_repository: TenantsRepositoryDep,
    tenant_domains_repository: TenantDomainsRepositoryDep,
    identity_provisioning_service: IdentityProvisioningServiceDep,
    runtime_schema_bootstrapper: RuntimeSchemaBootstrapperDep,
) -> CreateTenantUseCase:
    return CreateTenantUseCase(
        uow=uow,
        tenants_repository=tenants_repository,
        tenant_domains_repository=tenant_domains_repository,
        identity_provisioning_service=identity_provisioning_service,
        runtime_schema_bootstrapper=runtime_schema_bootstrapper,
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
    "CreateTenantUseCaseDep",
    "ResolveTenantByHostUseCaseDep",
    "TenantRequestContextByHostUseCaseDep",
    "get_create_tenant_use_case",
    "get_resolve_tenant_by_host_use_case",
    "get_tenant_request_context_by_host_use_case",
]
