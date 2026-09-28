from uuid import UUID
from fastapi import APIRouter, Query
from src.modules.crm.application.contact.query.list_available_contacts_query import (
    ListAvailableContactsQuery,
)
from src.modules.crm.presentation.depends.application import (
    ListAvailableContactsUseCaseDep,
)
from src.modules.crm.presentation.http.contact.responses import ContactListResponse
from src.modules.crm.domain.company.value_object import CompanyIdVO
from src.modules.crm.presentation.http.boundary import (
    context_ids,
    dto_values,
    http_errors,
)
from src.modules.shared.presentation.identity_context.depends import (
    AuthenticatedRequestContextDep,
)

router = APIRouter()


@router.get("/{company_id}/available-contacts", response_model=ContactListResponse)
async def list_available_contacts(
    company_id: UUID,
    context: AuthenticatedRequestContextDep,
    use_case: ListAvailableContactsUseCaseDep,
    q: str = Query(default="", max_length=255),
    limit: int = Query(default=25, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    with http_errors():
        tenant_id, _ = context_ids(context)
        result = await use_case(
            ListAvailableContactsQuery(
                tenant_id, CompanyIdVO.from_value(company_id), q, limit, offset
            )
        )
        return ContactListResponse(**dto_values(result))
