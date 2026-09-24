from fastapi import APIRouter, Query

from src.modules.crm.application.contact.query import ListContactsQuery
from src.modules.crm.presentation.depends import ListContactsUseCaseDep
from src.modules.crm.presentation.http.boundary import (
    context_ids,
    dto_values,
    http_errors,
)
from src.modules.crm.presentation.http.contact.responses import ContactListResponse
from src.modules.shared.presentation.identity_context.depends import (
    AuthenticatedRequestContextDep,
)

router = APIRouter()


@router.get("", response_model=ContactListResponse)
async def list_contacts(
    context: AuthenticatedRequestContextDep,
    use_case: ListContactsUseCaseDep,
    q: str = Query(default="", max_length=255),
    limit: int = Query(default=25, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    """Возвращает найденную страницу контактов текущего tenant."""
    with http_errors():
        tenant_id, _ = context_ids(context)
        result = await use_case(ListContactsQuery(tenant_id, q, limit, offset))
        return ContactListResponse(**dto_values(result))


__all__ = ["router"]
