from uuid import UUID

from fastapi import HTTPException

from src.modules.crm.application.contact.query.list_companies.query import (
    ListContactCompaniesQuery,
)
from src.modules.crm.domain.contact.error import ContactNotFoundError
from src.modules.crm.domain.contact.value_object.identifier import ContactIdVO
from src.modules.crm.presentation.contact.depends import (
    ListContactCompaniesHandlerDep,
)
from src.modules.crm.presentation.contact.http.response.list_companies import (
    ListContactCompanyItemResponse,
)
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)


async def list_contact_companies(
    contact_id: UUID,
    context: AuthenticatedRequestContextDep,
    handler: ListContactCompaniesHandlerDep,
) -> list[ListContactCompanyItemResponse]:
    principal = context.principal
    if principal is None or not principal.tenant_id:
        raise HTTPException(403, "Tenant context is required.")
    try:
        result = await handler.execute(
            ListContactCompaniesQuery(ContactIdVO.from_value(contact_id))
        )
    except ContactNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc
    return [ListContactCompanyItemResponse.from_dto(item) for item in result.companies]
