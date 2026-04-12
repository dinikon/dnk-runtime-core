from __future__ import annotations

from fastapi import APIRouter

from src.modules.tenancy.application.queries import ResolveTenantByHostQuery
from src.modules.shared.depends.request_host import RequestHostDep
from src.modules.tenancy.presentation.http.responses.console_tenants import (
    ResolveTenantResponseSchema,
)
from src.modules.tenancy.presentation.depends.application import (
    ResolveTenantByHostUseCaseDep,
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
