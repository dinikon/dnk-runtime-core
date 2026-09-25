from src.modules.shared.presentation.uuid.depends import UuidDep
from src.modules.crm.presentation.http.contact_points import contact_point_inputs
from uuid import UUID

from fastapi import APIRouter, Depends

from src.modules.crm.application.company.command import UpdateCompanyCommand
from src.modules.crm.domain.company.value_object import CompanyIdVO
from src.modules.crm.presentation.depends import UpdateCompanyUseCaseDep
from src.modules.crm.presentation.http.boundary import (
    context_ids,
    dto_values,
    http_errors,
)
from src.modules.crm.presentation.http.company.requests import UpdateCompanyRequest
from src.modules.crm.presentation.http.company.responses import CompanyResponse
from src.modules.identity.presentation.http.csrf import require_csrf
from src.modules.shared.presentation.identity_context.depends import (
    AuthenticatedRequestContextDep,
)

router = APIRouter()


@router.put(
    "/{company_id}",
    response_model=CompanyResponse,
    dependencies=[Depends(require_csrf)],
)
async def update_company(
    company_id: UUID,
    payload: UpdateCompanyRequest,
    context: AuthenticatedRequestContextDep,
    use_case: UpdateCompanyUseCaseDep,
    uuid_generator: UuidDep,
):
    """Полностью обновляет название компании текущего tenant."""
    with http_errors():
        tenant_id, actor_id = context_ids(context)
        result = await use_case(
            UpdateCompanyCommand(
                tenant_id=tenant_id,
                actor_id=actor_id,
                company_id=CompanyIdVO.from_value(company_id),
                **payload.model_dump(mode="json", exclude={"phones", "emails"}),
                **contact_point_inputs(payload, uuid_generator),
            )
        )
        return CompanyResponse(**dto_values(result))


__all__ = ["router"]
