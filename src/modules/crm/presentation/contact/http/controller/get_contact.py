from uuid import UUID

from fastapi import HTTPException

from src.modules.crm.application.contact.query.get_contact.query import GetContactQuery
from src.modules.crm.domain.contact.error import ContactNotFoundError
from src.modules.crm.domain.contact.value_object.identifier import ContactIdVO
from src.modules.crm.presentation.contact.depends import GetContactHandlerDep
from src.modules.crm.presentation.contact.http.response.get_contact import (
    GetContactResponse,
)
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)


async def get_contact(
    contact_id: UUID,
    context: AuthenticatedRequestContextDep,
    handler: GetContactHandlerDep,
) -> GetContactResponse:
    """Возвращает конкретный контакт только из tenant текущего участника."""
    principal = context.principal
    if principal is None or not principal.tenant_id:
        raise HTTPException(403, "Tenant context is required.")
    query = GetContactQuery(contact_id=ContactIdVO.from_value(contact_id))
    try:
        result = await handler.execute(query)
    except ContactNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc
    return GetContactResponse.from_dto(result)
