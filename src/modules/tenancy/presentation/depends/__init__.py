from src.modules.tenancy.presentation.depends.application import (
    CreateTenantUseCaseDep,
    ResolveTenantByHostUseCaseDep,
    TenantRequestContextByHostUseCaseDep,
    get_create_tenant_use_case,
    get_resolve_tenant_by_host_use_case,
    get_tenant_request_context_by_host_use_case,
)
from src.modules.tenancy.presentation.depends.infrastructure import (
    IdentityProvisioningServiceDep,
    TenantDomainsRepositoryDep,
    TenantOnboardingServiceDep,
    TenantsRepositoryDep,
    get_identity_provisioning_service,
    get_tenant_domains_repository,
    get_tenant_onboarding_service,
    get_tenants_repository,
)
from src.modules.tenancy.presentation.depends.security import (
    AdminCreateTenantAuthorizationDep,
    ControlPlaneApiKeyDep,
    authorize_control_plane_request,
    get_control_plane_api_key,
)

__all__ = [
    "AdminCreateTenantAuthorizationDep",
    "ControlPlaneApiKeyDep",
    "CreateTenantUseCaseDep",
    "IdentityProvisioningServiceDep",
    "ResolveTenantByHostUseCaseDep",
    "TenantDomainsRepositoryDep",
    "TenantOnboardingServiceDep",
    "TenantRequestContextByHostUseCaseDep",
    "TenantsRepositoryDep",
    "authorize_control_plane_request",
    "get_control_plane_api_key",
    "get_create_tenant_use_case",
    "get_identity_provisioning_service",
    "get_resolve_tenant_by_host_use_case",
    "get_tenant_domains_repository",
    "get_tenant_onboarding_service",
    "get_tenant_request_context_by_host_use_case",
    "get_tenants_repository",
]
