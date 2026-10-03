from uuid import UUID

from fastapi import HTTPException

from src.modules.crm.application.company.query.get_company.query import GetCompanyQuery
from src.modules.crm.domain.company.error import CompanyNotFoundError
from src.modules.crm.domain.company.value_object.identifier import CompanyIdVO
from src.modules.crm.presentation.company.depends import GetCompanyHandlerDep
from src.modules.crm.presentation.company.http.response.get_company import (
    GetCompanyResponse,
)
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)


async def get_company(
    company_id: UUID,
    context: AuthenticatedRequestContextDep,
    handler: GetCompanyHandlerDep,
) -> GetCompanyResponse:
    principal = context.principal
    if principal is None or not principal.tenant_id:
        raise HTTPException(403, "Tenant context is required.")
    try:
        result = await handler.execute(
            GetCompanyQuery(CompanyIdVO.from_value(company_id))
        )
    except CompanyNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc
    return GetCompanyResponse.from_dto(result)
