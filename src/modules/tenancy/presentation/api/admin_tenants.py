from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from src.modules.identity.domain.errors import UserEmailAlreadyExistsError
from src.modules.shared.domain.errors import ValidationError as DomainValidationError
from src.modules.tenancy.domain.domain.errors import (
    TenantDomainHostAlreadyExistsError,
)
from src.modules.tenancy.domain.tenant.errors import (
    TenantExternalIdAlreadyExistsError,
    TenantNameAlreadyExistsError,
)
from src.modules.tenancy.application.admin_onboarding.dto import (
    CreateTenantCommandDTO,
)
from src.modules.tenancy.presentation.api.requests.admin_tenants import (
    AdminCreateTenantRequestSchema,
)
from src.modules.tenancy.presentation.api.responses.admin_tenants import (
    AdminCreateTenantResponseSchema,
)
from src.modules.tenancy.presentation.depends.control_plane_auth import (
    AdminCreateTenantAuthorizationDep,
)
from src.modules.tenancy.presentation.depends.use_cases import CreateTenantUseCaseDep

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
    dto = CreateTenantCommandDTO(
        tenant_name=payload.tenant.name,
        external_id=payload.tenant.external_id,
        tenant_domain_host=payload.tenant_domain.host,
        user_last_name=payload.user.last_name,
        user_first_name=payload.user.first_name,
        user_email=str(payload.user_email.email),
    )

    try:
        result = await use_case.execute(dto)
    except (
        TenantNameAlreadyExistsError,
        TenantExternalIdAlreadyExistsError,
        UserEmailAlreadyExistsError,
        TenantDomainHostAlreadyExistsError,
    ) as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    except DomainValidationError as exc:
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
