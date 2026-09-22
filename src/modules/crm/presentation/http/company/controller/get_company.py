from uuid import UUID

from fastapi import APIRouter

from src.modules.crm.application.company.query import GetCompanyQuery
from src.modules.crm.domain.company.value_object import CompanyIdVO
from src.modules.crm.presentation.depends import GetCompanyUseCaseDep
from src.modules.crm.presentation.http.boundary import (
    context_ids,
    dto_values,
    http_errors,
)
from src.modules.crm.presentation.http.company.responses import CompanyResponse
from src.modules.shared.presentation.identity_context.depends import (
    AuthenticatedRequestContextDep,
)

router = APIRouter()


@router.get("/{company_id}", response_model=CompanyResponse)
async def get_company(
    company_id: UUID,
    context: AuthenticatedRequestContextDep,
    use_case: GetCompanyUseCaseDep,
):
    """Возвращает компанию текущего tenant."""
    with http_errors():
        tenant_id, _ = context_ids(context)
        result = await use_case(
            GetCompanyQuery(tenant_id, CompanyIdVO.from_value(company_id))
        )
        return CompanyResponse(**dto_values(result))


__all__ = ["router"]
