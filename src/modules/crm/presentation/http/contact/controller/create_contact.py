from fastapi import APIRouter, Depends

from src.modules.crm.application.contact.command import CreateContactCommand
from src.modules.crm.domain.contact.value_object import ContactIdVO
from src.modules.crm.presentation.depends import CreateContactUseCaseDep
from src.modules.crm.presentation.http.boundary import (
    context_ids,
    dto_values,
    http_errors,
)
from src.modules.crm.presentation.http.contact.requests import CreateContactRequest
from src.modules.crm.presentation.http.contact.responses import ContactResponse
from src.modules.identity.presentation.http.csrf import require_csrf
from src.modules.shared.presentation.identity_context.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.shared.presentation.uuid.depends import UuidDep

router = APIRouter()


@router.post(
    "",
    status_code=201,
    response_model=ContactResponse,
    dependencies=[Depends(require_csrf)],
)
async def create_contact(
    payload: CreateContactRequest,
    context: AuthenticatedRequestContextDep,
    use_case: CreateContactUseCaseDep,
    uuid_generator: UuidDep,
):
    """Создаёт контакт текущего tenant."""
    with http_errors():
        tenant_id, actor_id = context_ids(context)
        result = await use_case(
            CreateContactCommand(
                tenant_id=tenant_id,
                actor_id=actor_id,
                contact_id=ContactIdVO.from_value(uuid_generator.new()),
                **payload.model_dump(mode="json"),
            )
        )
        return ContactResponse(**dto_values(result))


__all__ = ["router"]
