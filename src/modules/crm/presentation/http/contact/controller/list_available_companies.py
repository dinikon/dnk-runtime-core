from uuid import UUID
from fastapi import APIRouter, Query
from src.modules.crm.application.company.query.list_available_companies_query import (
    ListAvailableCompaniesQuery,
)
from src.modules.crm.presentation.depends.application import (
    ListAvailableCompaniesUseCaseDep,
)
from src.modules.crm.presentation.http.company.responses import CompanyListResponse
from src.modules.crm.domain.contact.value_object import ContactIdVO
from src.modules.crm.presentation.http.boundary import (
    context_ids,
    dto_values,
    http_errors,
)
from src.modules.shared.presentation.identity_context.depends import (
    AuthenticatedRequestContextDep,
)

router = APIRouter()


@router.get("/{contact_id}/available-companies", response_model=CompanyListResponse)
async def list_available_companies(
    contact_id: UUID,
    context: AuthenticatedRequestContextDep,
    use_case: ListAvailableCompaniesUseCaseDep,
    q: str = Query(default="", max_length=255),
    limit: int = Query(default=25, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    with http_errors():
        tenant_id, _ = context_ids(context)
        result = await use_case(
            ListAvailableCompaniesQuery(
                tenant_id, ContactIdVO.from_value(contact_id), q, limit, offset
            )
        )
        return CompanyListResponse(**dto_values(result))
