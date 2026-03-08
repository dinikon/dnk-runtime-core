from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from src.modules.tenancy.application.admin_onboarding.use_cases.create_tenant import (
    CreateTenantUseCase,
)
from src.modules.tenancy.application.request_context_by_host.use_case import (
    GetTenantRequestContextByHostUseCase,
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
    RuntimeSchemaBootstrapperDep,
    TenantDataSourceServiceDep,
    TenantDomainServiceDep,
    TenantSchemaNameServiceDep,
    TenantSchemaProvisionerDep,
    TenantServiceDep,
)
from src.modules.shared.depends.uow import UoWDep


def get_create_tenant_use_case(
    uow: UoWDep,
    tenant_service: TenantServiceDep,
    identity_provisioning_service: IdentityProvisioningServiceDep,
    tenant_domain_service: TenantDomainServiceDep,
    tenant_schema_name_service: TenantSchemaNameServiceDep,
    tenant_schema_provisioner: TenantSchemaProvisionerDep,
    tenant_data_source_service: TenantDataSourceServiceDep,
    runtime_schema_bootstrapper: RuntimeSchemaBootstrapperDep,
) -> CreateTenantUseCase:
    return CreateTenantUseCase(
        uow=uow,
        tenant_service=tenant_service,
        identity_provisioning_service=identity_provisioning_service,
        tenant_domain_service=tenant_domain_service,
        tenant_schema_name_service=tenant_schema_name_service,
        tenant_schema_provisioner=tenant_schema_provisioner,
        tenant_data_source_service=tenant_data_source_service,
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
) -> GetTenantRequestContextByHostUseCase:
    return GetTenantRequestContextByHostUseCase(
        tenants_repository=tenants_repository,
        tenant_domains_repository=tenant_domains_repository,
    )


TenantRequestContextByHostUseCaseDep = Annotated[
    GetTenantRequestContextByHostUseCase,
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
