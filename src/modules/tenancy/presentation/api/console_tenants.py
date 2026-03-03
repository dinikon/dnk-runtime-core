from __future__ import annotations

from fastapi import APIRouter

from src.modules.tenancy.application.resolve_tenant_by_host.dto import (
    ResolveTenantByHostQueryDTO,
)
from src.modules.shared.depends.request_host import RequestHostDep
from src.modules.tenancy.presentation.api.responses.console_tenants import (
    ResolveTenantResponseSchema,
)
from src.modules.tenancy.presentation.depends.use_cases import (
    ResolveTenantByHostUseCaseDep,
)

router = APIRouter(tags=["console-tenants"])


@router.get(
    "/api/console/tenants/resolve",
    response_model=ResolveTenantResponseSchema,
)
async def resolve_tenant(
    host: RequestHostDep,
    use_case: ResolveTenantByHostUseCaseDep,
) -> ResolveTenantResponseSchema:
    result = await use_case.execute(ResolveTenantByHostQueryDTO(host=host))
    return ResolveTenantResponseSchema(
        exists=result.exists,
        available=result.available,
        status=result.status,
        tenant_id=result.tenant_id,
        api_host=result.api_host,
    )
