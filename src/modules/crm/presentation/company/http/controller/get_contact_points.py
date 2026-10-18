from uuid import UUID

from fastapi import HTTPException

from src.modules.crm.application.company.query.list_contact_points.query import (
    ListCompanyContactPointsQuery,
)
from src.modules.crm.domain.company.error import CompanyNotFoundError
from src.modules.crm.domain.company.value_object.identifier import CompanyIdVO
from src.modules.crm.presentation.company.depends import (
    ListCompanyContactPointsHandlerDep,
)
from src.modules.crm.presentation.company.http.response.get_contact_points import (
    GetCompanyContactPointsResponse,
)
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


async def get_company_contact_points(
    company_id: UUID,
    context: AuthenticatedRequestContextDep,
    handler: ListCompanyContactPointsHandlerDep,
) -> GetCompanyContactPointsResponse:
    """Читает контактные данные company."""
    principal = context.principal
    if principal is None or not principal.tenant_id:
        raise HTTPException(403, "Tenant context is required.")
    tenant_id = EntityIdVO.from_value(principal.tenant_id)
    try:
        result = await handler.execute(
            ListCompanyContactPointsQuery(tenant_id, CompanyIdVO.from_value(company_id))
        )
    except CompanyNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc
    return GetCompanyContactPointsResponse.from_dto(result)
