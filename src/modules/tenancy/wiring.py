from __future__ import annotations

import secrets
from typing import Annotated

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.config import dnk_config
from src.modules.identity.application.provisioning.services.user_service import (
    UserService,
)
from src.modules.identity.infrastructure.repositories import SqlAlchemyUserRepository
from src.modules.shared.depends.uow import UoWDep
from src.modules.tenancy.application.ports.identity import (
    IdentityProvisioningServiceProtocol,
)
from src.modules.tenancy.application.use_cases import (
    CreateTenantUseCase,
    ResolveTenantByHostUseCase,
    ResolveTenantRequestContextByHostUseCase,
)
from src.modules.tenancy.domain.repositories import (
    TenantDomainRepositoryProtocol,
    TenantRepositoryProtocol,
)
from src.modules.tenancy.infrastructure.identity_provisioning import (
    IdentityProvisioningServiceAdapter,
)
from src.modules.tenancy.infrastructure.repositories import (
    SqlAlchemyTenantDomainRepository,
    SqlAlchemyTenantRepository,
)

control_plane_bearer_scheme = HTTPBearer(
    auto_error=False,
    scheme_name="ControlPlaneBearer",
    description="ControlPlane API key in format: Bearer <API_KEY>",
)


def get_control_plane_api_key() -> str:
    return dnk_config.CONTROL_PLANE_API_KEY


ControlPlaneApiKeyDep = Annotated[str, Depends(get_control_plane_api_key)]


async def authorize_control_plane_request(
    control_plane_api_key: ControlPlaneApiKeyDep,
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Security(control_plane_bearer_scheme),
    ] = None,
) -> None:
    if not control_plane_api_key:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Control plane API key is not configured.",
        )

    if (
        credentials is None
        or credentials.scheme != "Bearer"
        or not credentials.credentials
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not secrets.compare_digest(credentials.credentials, control_plane_api_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized.",
            headers={"WWW-Authenticate": "Bearer"},
        )


AdminCreateTenantAuthorizationDep = Annotated[
    None,
    Depends(authorize_control_plane_request),
]


def get_tenants_repository(uow: UoWDep) -> TenantRepositoryProtocol:
    return SqlAlchemyTenantRepository(uow.session)


TenantsRepositoryDep = Annotated[
    TenantRepositoryProtocol,
    Depends(get_tenants_repository),
]


def get_tenant_domains_repository(uow: UoWDep) -> TenantDomainRepositoryProtocol:
    return SqlAlchemyTenantDomainRepository(uow.session)


TenantDomainsRepositoryDep = Annotated[
    TenantDomainRepositoryProtocol,
    Depends(get_tenant_domains_repository),
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


def get_create_tenant_use_case(
    uow: UoWDep,
    tenants_repository: TenantsRepositoryDep,
    tenant_domains_repository: TenantDomainsRepositoryDep,
    identity_provisioning_service: IdentityProvisioningServiceDep,
) -> CreateTenantUseCase:
    return CreateTenantUseCase(
        uow=uow,
        tenants_repository=tenants_repository,
        tenant_domains_repository=tenant_domains_repository,
        identity_provisioning_service=identity_provisioning_service,
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
    "AdminCreateTenantAuthorizationDep",
    "ControlPlaneApiKeyDep",
    "CreateTenantUseCaseDep",
    "IdentityProvisioningServiceDep",
    "ResolveTenantByHostUseCaseDep",
    "TenantDomainsRepositoryDep",
    "TenantRequestContextByHostUseCaseDep",
    "TenantsRepositoryDep",
    "authorize_control_plane_request",
    "get_control_plane_api_key",
    "get_create_tenant_use_case",
    "get_identity_provisioning_service",
    "get_resolve_tenant_by_host_use_case",
    "get_tenant_domains_repository",
    "get_tenant_request_context_by_host_use_case",
    "get_tenants_repository",
]
