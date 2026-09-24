from uuid import UUID

from fastapi import APIRouter

from src.modules.crm.application.contact.query import GetContactQuery
from src.modules.crm.domain.contact.value_object import ContactIdVO
from src.modules.crm.presentation.depends import GetContactUseCaseDep
from src.modules.crm.presentation.http.boundary import (
    context_ids,
    dto_values,
    http_errors,
)
from src.modules.crm.presentation.http.contact.responses import ContactResponse
from src.modules.shared.presentation.identity_context.depends import (
    AuthenticatedRequestContextDep,
)

router = APIRouter()


@router.get("/{contact_id}", response_model=ContactResponse)
async def get_contact(
    contact_id: UUID,
    context: AuthenticatedRequestContextDep,
    use_case: GetContactUseCaseDep,
):
    """Возвращает контакт текущего tenant."""
    with http_errors():
        tenant_id, _ = context_ids(context)
        result = await use_case(
            GetContactQuery(tenant_id, ContactIdVO.from_value(contact_id))
        )
        return ContactResponse(**dto_values(result))


__all__ = ["router"]
