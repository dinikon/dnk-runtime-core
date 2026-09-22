from uuid import UUID

from fastapi import APIRouter, Depends, Response

from src.modules.crm.application.contact.command import DeleteContactCommand
from src.modules.crm.domain.contact.value_object import ContactIdVO
from src.modules.crm.presentation.depends import DeleteContactUseCaseDep
from src.modules.crm.presentation.http.boundary import context_ids, http_errors
from src.modules.identity.presentation.http.csrf import require_csrf
from src.modules.shared.presentation.identity_context.depends import (
    AuthenticatedRequestContextDep,
)

router = APIRouter()


@router.delete("/{contact_id}", status_code=204, dependencies=[Depends(require_csrf)])
async def delete_contact(
    contact_id: UUID,
    context: AuthenticatedRequestContextDep,
    use_case: DeleteContactUseCaseDep,
):
    """Физически удаляет контакт текущего tenant."""
    with http_errors():
        tenant_id, _ = context_ids(context)
        await use_case(
            DeleteContactCommand(tenant_id, ContactIdVO.from_value(contact_id))
        )
        return Response(status_code=204)


__all__ = ["router"]
