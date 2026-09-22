from fastapi import APIRouter, Query

from src.modules.crm.application.company.query import ListCompaniesQuery
from src.modules.crm.presentation.depends import ListCompaniesUseCaseDep
from src.modules.crm.presentation.http.boundary import (
    context_ids,
    dto_values,
    http_errors,
)
from src.modules.crm.presentation.http.company.responses import CompanyListResponse
from src.modules.shared.presentation.identity_context.depends import (
    AuthenticatedRequestContextDep,
)

router = APIRouter()


@router.get("", response_model=CompanyListResponse)
async def list_companies(
    context: AuthenticatedRequestContextDep,
    use_case: ListCompaniesUseCaseDep,
    q: str = Query(default="", max_length=255),
    limit: int = Query(default=25, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    """Возвращает найденную страницу компаний текущего tenant."""
    with http_errors():
        tenant_id, _ = context_ids(context)
        result = await use_case(ListCompaniesQuery(tenant_id, q, limit, offset))
        return CompanyListResponse(**dto_values(result))


__all__ = ["router"]
