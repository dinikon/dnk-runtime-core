from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from src.modules.identity.domain import UserEmailAlreadyExistsError
from src.modules.schema_registry.domain.error import (
    DataSourceAlreadyExistsError,
    PhysicalSchemaAlreadyExistsError,
)
from src.modules.shared import DomainError as DomainDomainError
from src.modules.tenancy.application.tenant.command import CreateTenantCommand
from src.modules.tenancy.domain.tenant import (
    TenantExternalIdAlreadyExistsError,
    TenantNameAlreadyExistsError,
)
from src.modules.tenancy.domain.tenant_domain import (
    TenantDomainHostAlreadyExistsError,
)
from src.modules.tenancy.presentation.depends.application import (
    CreateTenantUseCaseDep,
)
from src.modules.tenancy.presentation.depends.security import (
    AdminCreateTenantAuthorizationDep,
)
from src.modules.tenancy.presentation.http.admin_tenant.requests import (
    AdminCreateTenantRequestSchema,
)
from src.modules.tenancy.presentation.http.admin_tenant.responses import (
    AdminCreateTenantResponseSchema,
)

router = APIRouter(tags=["admin-tenants"])


@router.post(
    "/admin/create-tenant",
    response_model=AdminCreateTenantResponseSchema,
)
async def create_tenant(
    payload: AdminCreateTenantRequestSchema,
    _: AdminCreateTenantAuthorizationDep,
    use_case: CreateTenantUseCaseDep,
) -> AdminCreateTenantResponseSchema:
    """HTTP endpoint создания tenant через защищенный control-plane вызов."""

    command = CreateTenantCommand(
        tenant_name=payload.tenant.name,
        external_id=payload.tenant.external_id,
        tenant_domain_host=payload.tenant_domain.host,
        user_last_name=payload.user.last_name,
        user_first_name=payload.user.first_name,
        user_email=str(payload.user_email.email),
    )

    try:
        result = await use_case.execute(command)
    except (
        TenantNameAlreadyExistsError,
        TenantExternalIdAlreadyExistsError,
        UserEmailAlreadyExistsError,
        TenantDomainHostAlreadyExistsError,
        DataSourceAlreadyExistsError,
        PhysicalSchemaAlreadyExistsError,
    ) as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    except DomainDomainError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    return AdminCreateTenantResponseSchema(
        tenant_id=result.tenant_id,
        user_id=result.user_id,
        user_email_id=result.user_email_id,
        tenant_domain_id=result.tenant_domain_id,
        tenant_status=result.tenant_status,
        user_status=result.user_status,
        tenant_domain_host=result.tenant_domain_host,
    )


__all__ = ["router"]
