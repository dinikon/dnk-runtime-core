from uuid import UUID

from fastapi import HTTPException

from src.modules.crm.application.contact.command.update_contact.command import (
    UpdateContactCommand,
)
from src.modules.crm.domain.contact.error import (
    ContactNotFoundError,
    InvalidContactNameError,
)
from src.modules.crm.domain.contact.value_object.identifier import ContactIdVO
from src.modules.crm.presentation.contact.depends import UpdateContactHandlerDep
from src.modules.crm.presentation.contact.http.request.patch_contact import (
    PatchContactRequest,
)
from src.modules.crm.presentation.contact.http.response.patch_contact import (
    PatchContactResponse,
)
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


async def patch_contact(
    contact_id: UUID,
    payload: PatchContactRequest,
    context: AuthenticatedRequestContextDep,
    handler: UpdateContactHandlerDep,
) -> PatchContactResponse:
    """Обновляет только переданные части ФИО."""
    principal = context.principal
    if principal is None or not principal.tenant_id:
        raise HTTPException(403, "Tenant context is required.")
    command = UpdateContactCommand(
        contact_id=ContactIdVO.from_value(contact_id),
        actor_id=EntityIdVO.from_value(principal.user_id),
        fields=frozenset(payload.model_fields_set),
        first_name=payload.first_name,
        last_name=payload.last_name,
        middle_name=payload.middle_name,
    )
    try:
        result = await handler.execute(command)
    except ContactNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc
    except InvalidContactNameError as exc:
        raise HTTPException(422, str(exc)) from exc
    return PatchContactResponse.from_dto(result)
