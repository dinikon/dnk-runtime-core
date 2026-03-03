from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from src.modules.tenancy.application.admin_onboarding.use_cases.create_tenant import (
    CreateTenantUseCase,
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

__all__ = ["get_create_tenant_use_case", "CreateTenantUseCaseDep"]
