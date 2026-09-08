from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from src.config import dnk_config
from src.modules.shared.presentation.persistence.depends import UoWDep
from src.modules.shared.infrastructure.persistence.tenant_migrations import (
    TenantMigrator,
)
from src.modules.tenancy.infrastructure.adapter.schema_bootstrap import (
    AlembicTenantSchemaBootstrapAdapter,
)
from src.modules.tenancy.application.ports.schema_bootstrap import (
    TenantSchemaBootstrapContextFactory,
    TenantSchemaBootstrapPort,
)
from src.modules.tenancy.application.tenant import CreateTenantUseCase
from src.modules.tenancy.application.tenant_domain.use_case import (
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
    """Создает use case полного tenant onboarding."""

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
    """Создает фабрику bootstrap context из tenant schema конфигурации."""
    return TenantSchemaBootstrapContextFactory(
        schema_prefix=dnk_config.SCHEMA_PREFIX,
    )


TenantSchemaBootstrapContextFactoryDep = Annotated[
    TenantSchemaBootstrapContextFactory,
    Depends(get_tenant_schema_bootstrap_context_factory),
]


def get_tenant_schema_bootstrap_port(
    uow: UoWDep,
) -> TenantSchemaBootstrapPort:
    """Создает порт bootstrap на соединении текущего UoW."""
    return AlembicTenantSchemaBootstrapAdapter(uow.session, TenantMigrator())


TenantSchemaBootstrapPortDep = Annotated[
    TenantSchemaBootstrapPort,
    Depends(get_tenant_schema_bootstrap_port),
]


def get_resolve_tenant_by_host_use_case(
    tenants_repository: TenantsRepositoryDep,
    tenant_domains_repository: TenantDomainsRepositoryDep,
) -> ResolveTenantByHostUseCase:
    """Создает use case публичного resolve tenant по host."""
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
    """Создает use case внутреннего tenant request context по host."""
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
