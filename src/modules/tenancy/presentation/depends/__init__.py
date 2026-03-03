from src.modules.tenancy.presentation.depends.authorization import (
    AuthorizationServiceDep,
    authorize_admin_create_tenant,
    get_authorization_service,
)
from src.modules.tenancy.presentation.depends.control_plane_auth import (
    AdminCreateTenantAuthorizationDep,
    ControlPlaneApiKeyDep,
    authorize_control_plane_request,
    get_control_plane_api_key,
)
from src.modules.tenancy.presentation.depends.repositories import (
    TenantDomainsRepositoryDep,
    TenantsRepositoryDep,
    get_tenant_domains_repository,
    get_tenants_repository,
)
from src.modules.tenancy.presentation.depends.services import (
    IdentityProvisioningServiceDep,
    TenantDomainServiceDep,
    TenantServiceDep,
    get_identity_provisioning_service,
    get_tenant_domain_service,
    get_tenant_service,
)
from src.modules.tenancy.presentation.depends.use_cases import (
    CreateTenantUseCaseDep,
    ResolveTenantByHostUseCaseDep,
    get_create_tenant_use_case,
    get_resolve_tenant_by_host_use_case,
)

__all__ = [
    "get_authorization_service",
    "AuthorizationServiceDep",
    "authorize_admin_create_tenant",
    "get_control_plane_api_key",
    "ControlPlaneApiKeyDep",
    "authorize_control_plane_request",
    "AdminCreateTenantAuthorizationDep",
    "get_tenants_repository",
    "TenantsRepositoryDep",
    "get_tenant_domains_repository",
    "TenantDomainsRepositoryDep",
    "get_tenant_service",
    "TenantServiceDep",
    "get_tenant_domain_service",
    "TenantDomainServiceDep",
    "get_identity_provisioning_service",
    "IdentityProvisioningServiceDep",
    "get_create_tenant_use_case",
    "CreateTenantUseCaseDep",
    "get_resolve_tenant_by_host_use_case",
    "ResolveTenantByHostUseCaseDep",
]
