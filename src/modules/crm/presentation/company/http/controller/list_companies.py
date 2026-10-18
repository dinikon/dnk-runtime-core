from fastapi import HTTPException

from src.modules.crm.application.company.query.list_companies.query import (
    ListCompaniesQuery,
)
from src.modules.crm.presentation.company.depends import ListCompaniesHandlerDep
from src.modules.crm.presentation.company.http.response.list_companies import (
    ListCompanyItemResponse,
)
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)


async def list_companies(
    context: AuthenticatedRequestContextDep,
    handler: ListCompaniesHandlerDep,
) -> list[ListCompanyItemResponse]:
    principal = context.principal
    if principal is None or not principal.tenant_id:
        raise HTTPException(403, "Tenant context is required.")
    result = await handler.execute(ListCompaniesQuery())
    return [ListCompanyItemResponse.from_dto(item) for item in result.companies]
