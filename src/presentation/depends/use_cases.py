from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from src.application.admin_tenants.use_cases.create_tenant import CreateTenantUseCase
from src.presentation.depends.services import (
    TenantDomainServiceDep,
    TenantServiceDep,
    UserServiceDep,
)
from src.presentation.depends.uow import UoWDep


def get_create_tenant_use_case(
    uow: UoWDep,
    tenant_service: TenantServiceDep,
    user_service: UserServiceDep,
    tenant_domain_service: TenantDomainServiceDep,
) -> CreateTenantUseCase:
    return CreateTenantUseCase(
        uow=uow,
        tenant_service=tenant_service,
        user_service=user_service,
        tenant_domain_service=tenant_domain_service,
    )


CreateTenantUseCaseDep = Annotated[
    CreateTenantUseCase,
    Depends(get_create_tenant_use_case),
]

__all__ = ["get_create_tenant_use_case", "CreateTenantUseCaseDep"]
