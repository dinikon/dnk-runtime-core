from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from src.config import dnk_config
from src.modules.schema_registry.presentation.depends.application import (
    CreateSchemaUseCaseDep,
)
from src.modules.schema_registry.infrastructure.tenancy_schema_bootstrap_adapter import (
    SchemaRegistryTenantSchemaBootstrapAdapter,
)
from src.modules.tenancy.application.ports.schema_bootstrap import (
    TenantSchemaBootstrapContextFactory,
    TenantSchemaBootstrapPort,
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
    tenant_schema_bootstrap_context_factory: "TenantSchemaBootstrapContextFactoryDep",
    tenant_schema_bootstrap_port: "TenantSchemaBootstrapPortDep",
) -> CreateTenantUseCase:
    return CreateTenantUseCase(
        tenant_onboarding_service=tenant_onboarding_service,
        identity_provisioning_service=identity_provisioning_service,
        tenant_schema_bootstrap_context_factory=tenant_schema_bootstrap_context_factory,
        tenant_schema_bootstrap_port=tenant_schema_bootstrap_port,
    )


CreateTenantUseCaseDep = Annotated[
    CreateTenantUseCase,
    Depends(get_create_tenant_use_case),
]


def get_tenant_schema_bootstrap_context_factory() -> (
    TenantSchemaBootstrapContextFactory
):
    return TenantSchemaBootstrapContextFactory(
        schema_prefix=dnk_config.SCHEMA_PREFIX,
        default_seed_path=dnk_config.DEFAULT_SEED_MODULE,
    )


TenantSchemaBootstrapContextFactoryDep = Annotated[
    TenantSchemaBootstrapContextFactory,
    Depends(get_tenant_schema_bootstrap_context_factory),
]


def get_tenant_schema_bootstrap_port(
    create_schema_use_case: CreateSchemaUseCaseDep,
) -> TenantSchemaBootstrapPort:
    return SchemaRegistryTenantSchemaBootstrapAdapter(create_schema_use_case)


TenantSchemaBootstrapPortDep = Annotated[
    TenantSchemaBootstrapPort,
    Depends(get_tenant_schema_bootstrap_port),
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
    "TenantSchemaBootstrapContextFactoryDep",
    "TenantSchemaBootstrapPortDep",
    "TenantRequestContextByHostUseCaseDep",
    "get_create_tenant_use_case",
    "get_resolve_tenant_by_host_use_case",
    "get_tenant_schema_bootstrap_context_factory",
    "get_tenant_schema_bootstrap_port",
    "get_tenant_request_context_by_host_use_case",
]
