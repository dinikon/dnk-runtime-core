from uuid import UUID

from fastapi import HTTPException

from src.modules.crm.application.company.query.list_contacts.query import (
    ListCompanyContactsQuery,
)
from src.modules.crm.domain.company.error import CompanyNotFoundError
from src.modules.crm.domain.company.value_object.identifier import CompanyIdVO
from src.modules.crm.presentation.company.depends import ListCompanyContactsHandlerDep
from src.modules.crm.presentation.company.http.response.list_contacts import (
    ListCompanyContactItemResponse,
)
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)


async def list_company_contacts(
    company_id: UUID,
    context: AuthenticatedRequestContextDep,
    handler: ListCompanyContactsHandlerDep,
) -> list[ListCompanyContactItemResponse]:
    principal = context.principal
    if principal is None or not principal.tenant_id:
        raise HTTPException(403, "Tenant context is required.")
    try:
        result = await handler.execute(
            ListCompanyContactsQuery(CompanyIdVO.from_value(company_id))
        )
    except CompanyNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc
    return [ListCompanyContactItemResponse.from_dto(item) for item in result.contacts]
