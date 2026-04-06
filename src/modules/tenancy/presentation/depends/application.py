from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from src.modules.schema_registry.presentation.depends.application import (
    CreateSchemaUseCaseDep,
)
from src.modules.tenancy.application.use_cases import (
    CreateTenantUseCase,
    ResolveTenantByHostUseCase,
    ResolveTenantRequestContextByHostUseCase,
)
from src.modules.tenancy.presentation.depends.infrastructure import (
    IdentityProvisioningServiceDep,
    TenantDomainsRepositoryDep,
    TenantOnboardingServiceDep,
    TenantsRepositoryDep,
)


def get_create_tenant_use_case(
    tenant_onboarding_service: TenantOnboardingServiceDep,
    identity_provisioning_service: IdentityProvisioningServiceDep,
    create_schema_use_case: CreateSchemaUseCaseDep,
) -> CreateTenantUseCase:
    return CreateTenantUseCase(
        tenant_onboarding_service=tenant_onboarding_service,
        identity_provisioning_service=identity_provisioning_service,
        create_schema_use_case=create_schema_use_case,
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
