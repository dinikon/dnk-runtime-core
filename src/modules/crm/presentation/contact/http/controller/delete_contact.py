from uuid import UUID

from fastapi import HTTPException, Response

from src.modules.crm.application.contact.command.delete_contact.command import (
    DeleteContactCommand,
)
from src.modules.crm.domain.contact.error import ContactNotFoundError
from src.modules.crm.domain.contact.value_object.identifier import ContactIdVO
from src.modules.crm.presentation.contact.depends import DeleteContactHandlerDep
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)


async def delete_contact(
    contact_id: UUID,
    context: AuthenticatedRequestContextDep,
    handler: DeleteContactHandlerDep,
) -> Response:
    """Физически удаляет контакт в tenant текущего участника."""
    principal = context.principal
    if principal is None or not principal.tenant_id:
        raise HTTPException(403, "Tenant context is required.")
    try:
        await handler.execute(DeleteContactCommand(ContactIdVO.from_value(contact_id)))
    except ContactNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc
    return Response(status_code=204)
