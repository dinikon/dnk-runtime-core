from src.modules.shared.presentation.uuid.depends import UuidDep
from src.modules.crm.presentation.http.contact_points import contact_point_inputs
from uuid import UUID

from fastapi import APIRouter, Depends

from src.modules.crm.application.contact.command import UpdateContactCommand
from src.modules.crm.domain.contact.value_object import ContactIdVO
from src.modules.crm.presentation.depends import UpdateContactUseCaseDep
from src.modules.crm.presentation.http.boundary import (
    context_ids,
    dto_values,
    http_errors,
)
from src.modules.crm.presentation.http.contact.requests import UpdateContactRequest
from src.modules.crm.presentation.http.contact.responses import ContactResponse
from src.modules.identity.presentation.http.csrf import require_csrf
from src.modules.shared.presentation.identity_context.depends import (
    AuthenticatedRequestContextDep,
)

router = APIRouter()


@router.put(
    "/{contact_id}",
    response_model=ContactResponse,
    dependencies=[Depends(require_csrf)],
)
async def update_contact(
    contact_id: UUID,
    payload: UpdateContactRequest,
    context: AuthenticatedRequestContextDep,
    use_case: UpdateContactUseCaseDep,
    uuid_generator: UuidDep,
):
    """Полностью обновляет ФИО контакта текущего tenant."""
    with http_errors():
        tenant_id, actor_id = context_ids(context)
        result = await use_case(
            UpdateContactCommand(
                tenant_id=tenant_id,
                actor_id=actor_id,
                contact_id=ContactIdVO.from_value(contact_id),
                **payload.model_dump(mode="json", exclude={"phones", "emails"}),
                **contact_point_inputs(payload, uuid_generator),
            )
        )
        return ContactResponse(**dto_values(result))


__all__ = ["router"]
