from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Request
from pydantic import BaseModel

from src.modules.tenancy.application.resolve_tenant_by_host.dto import (
    ResolveTenantByHostQueryDTO,
)
from src.modules.tenancy.presentation.depends.use_cases import (
    ResolveTenantByHostUseCaseDep,
)

router = APIRouter(tags=["console-tenants"])


class ResolveTenantResponseSchema(BaseModel):
    exists: bool
    available: bool
    status: str
    tenant_id: UUID | None
    api_host: str | None


@router.get(
    "/api/console/tenants/resolve",
    response_model=ResolveTenantResponseSchema,
)
async def resolve_tenant(
    request: Request,
    use_case: ResolveTenantByHostUseCaseDep,
) -> ResolveTenantResponseSchema:
    host = request.url.hostname or request.headers.get("host", "")
    result = await use_case.execute(ResolveTenantByHostQueryDTO(host=host))
    return ResolveTenantResponseSchema(
        exists=result.exists,
        available=result.available,
        status=result.status,
        tenant_id=result.tenant_id,
        api_host=result.api_host,
    )
