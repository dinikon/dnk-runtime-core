from uuid import UUID

from fastapi import APIRouter, Depends, Response

from src.modules.crm.application.company.command import DeleteCompanyCommand
from src.modules.crm.domain.company.value_object import CompanyIdVO
from src.modules.crm.presentation.depends import DeleteCompanyUseCaseDep
from src.modules.crm.presentation.http.boundary import context_ids, http_errors
from src.modules.identity.presentation.http.csrf import require_csrf
from src.modules.shared.presentation.identity_context.depends import (
    AuthenticatedRequestContextDep,
)

router = APIRouter()


@router.delete("/{company_id}", status_code=204, dependencies=[Depends(require_csrf)])
async def delete_company(
    company_id: UUID,
    context: AuthenticatedRequestContextDep,
    use_case: DeleteCompanyUseCaseDep,
):
    """Физически удаляет компанию текущего tenant."""
    with http_errors():
        tenant_id, _ = context_ids(context)
        await use_case(
            DeleteCompanyCommand(tenant_id, CompanyIdVO.from_value(company_id))
        )
        return Response(status_code=204)


__all__ = ["router"]
