from fastapi import APIRouter, Depends

from src.modules.crm.application.company.command import CreateCompanyCommand
from src.modules.crm.domain.company.value_object import CompanyIdVO
from src.modules.crm.presentation.depends import CreateCompanyUseCaseDep
from src.modules.crm.presentation.http.boundary import (
    context_ids,
    dto_values,
    http_errors,
)
from src.modules.crm.presentation.http.company.requests import CreateCompanyRequest
from src.modules.crm.presentation.http.company.responses import CompanyResponse
from src.modules.identity.presentation.http.csrf import require_csrf
from src.modules.shared.presentation.identity_context.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.shared.presentation.uuid.depends import UuidDep

router = APIRouter()


@router.post(
    "",
    status_code=201,
    response_model=CompanyResponse,
    dependencies=[Depends(require_csrf)],
)
async def create_company(
    payload: CreateCompanyRequest,
    context: AuthenticatedRequestContextDep,
    use_case: CreateCompanyUseCaseDep,
    uuid_generator: UuidDep,
):
    """Создаёт компанию текущего tenant."""
    with http_errors():
        tenant_id, actor_id = context_ids(context)
        result = await use_case(
            CreateCompanyCommand(
                tenant_id=tenant_id,
                actor_id=actor_id,
                company_id=CompanyIdVO.from_value(uuid_generator.new()),
                **payload.model_dump(mode="json"),
            )
        )
        return CompanyResponse(**dto_values(result))


__all__ = ["router"]
