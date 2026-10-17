from fastapi import HTTPException

from src.modules.crm.application.contact.query.list_contacts.query import (
    ListContactsQuery,
)
from src.modules.crm.presentation.contact.depends import ListContactsHandlerDep
from src.modules.crm.presentation.contact.http.response.list_contacts import (
    ListContactItemResponse,
)
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)


async def list_contacts(
    context: AuthenticatedRequestContextDep,
    handler: ListContactsHandlerDep,
) -> list[ListContactItemResponse]:
    """Возвращает все контакты текущего tenant."""
    principal = context.principal
    if principal is None or not principal.tenant_id:
        raise HTTPException(403, "Tenant context is required.")
    result = await handler.execute(ListContactsQuery())
    return [ListContactItemResponse.from_dto(contact) for contact in result.contacts]
