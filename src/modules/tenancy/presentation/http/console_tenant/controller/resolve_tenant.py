from __future__ import annotations

from fastapi import APIRouter

from src.modules.shared.presentation.http.depends import RequestHostDep
from src.modules.tenancy.application.tenant_domain.query import (
    ResolveTenantByHostQuery,
)
from src.modules.tenancy.presentation.depends.application import (
    ResolveTenantByHostUseCaseDep,
)
from src.modules.tenancy.presentation.http.console_tenant.responses import (
    ResolveTenantResponseSchema,
)

router = APIRouter(tags=["console-tenants"])


@router.get(
    "/console/tenants/resolve",
    response_model=ResolveTenantResponseSchema,
)
async def resolve_tenant(
    host: RequestHostDep,
    use_case: ResolveTenantByHostUseCaseDep,
) -> ResolveTenantResponseSchema:
    """HTTP endpoint resolve tenant по host текущего request."""

    result = await use_case.execute(ResolveTenantByHostQuery(host=host))
    return ResolveTenantResponseSchema(
        exists=result.exists,
        available=result.available,
        status=result.status,
        tenant_id=result.tenant_id,
        api_host=result.api_host,
    )


__all__ = ["router"]
