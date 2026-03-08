from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from src.modules.identity.presentation.depends.services import UserServiceDep
from src.modules.tenancy.application.admin_onboarding.ports.identity import (
    IdentityProvisioningServiceProtocol,
)
from src.modules.tenancy.application.admin_onboarding.ports.storage import (
    TenantSchemaProvisionerProtocol,
)
from src.modules.tenancy.application.admin_onboarding.services.tenant_data_source_service import (
    TenantDataSourceService,
    TenantDataSourceServiceProtocol,
)
from src.modules.tenancy.application.admin_onboarding.services.tenant_domain_service import (
    TenantDomainService,
    TenantDomainServiceProtocol,
)
from src.modules.tenancy.application.admin_onboarding.services.tenant_schema_name_service import (
    TenantSchemaNameService,
    TenantSchemaNameServiceProtocol,
)
from src.modules.tenancy.application.admin_onboarding.services.tenant_service import (
    TenantService,
    TenantServiceProtocol,
)
from src.modules.tenancy.infrastructure.identity_provisioning_service import (
    IdentityProvisioningServiceAdapter,
)
from src.modules.tenancy.infrastructure.schema_provisioner import (
    SqlAlchemyTenantSchemaProvisioner,
)
from src.modules.tenancy.presentation.depends.repositories import (
    TenantDataSourcesRepositoryDep,
    TenantDomainsRepositoryDep,
    TenantsRepositoryDep,
)
from src.modules.shared.depends.uow import UoWDep


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
    user_service: UserServiceDep,
) -> IdentityProvisioningServiceProtocol:
    return IdentityProvisioningServiceAdapter(user_service)


IdentityProvisioningServiceDep = Annotated[
    IdentityProvisioningServiceProtocol,
    Depends(get_identity_provisioning_service),
]


def get_tenant_schema_name_service() -> TenantSchemaNameServiceProtocol:
    return TenantSchemaNameService()


TenantSchemaNameServiceDep = Annotated[
    TenantSchemaNameServiceProtocol,
    Depends(get_tenant_schema_name_service),
]


def get_tenant_schema_provisioner(
    uow: UoWDep,
) -> TenantSchemaProvisionerProtocol:
    return SqlAlchemyTenantSchemaProvisioner(uow.session)


TenantSchemaProvisionerDep = Annotated[
    TenantSchemaProvisionerProtocol,
    Depends(get_tenant_schema_provisioner),
]


def get_tenant_data_source_service(
    tenant_data_sources_repository: TenantDataSourcesRepositoryDep,
) -> TenantDataSourceServiceProtocol:
    return TenantDataSourceService(tenant_data_sources_repository)


TenantDataSourceServiceDep = Annotated[
    TenantDataSourceServiceProtocol,
    Depends(get_tenant_data_source_service),
]

__all__ = [
    "IdentityProvisioningServiceAdapter",
    "get_tenant_service",
    "TenantServiceDep",
    "get_tenant_domain_service",
    "TenantDomainServiceDep",
    "get_identity_provisioning_service",
    "IdentityProvisioningServiceDep",
    "get_tenant_schema_name_service",
    "TenantSchemaNameServiceDep",
    "get_tenant_schema_provisioner",
    "TenantSchemaProvisionerDep",
    "get_tenant_data_source_service",
    "TenantDataSourceServiceDep",
]
