from uuid import UUID

from fastapi import HTTPException, Response

from src.modules.crm.application.company.command.delete_company.command import (
    DeleteCompanyCommand,
)
from src.modules.crm.domain.company.error import CompanyNotFoundError
from src.modules.crm.domain.company.value_object.identifier import CompanyIdVO
from src.modules.crm.presentation.company.depends import DeleteCompanyHandlerDep
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)


async def delete_company(
    company_id: UUID,
    context: AuthenticatedRequestContextDep,
    handler: DeleteCompanyHandlerDep,
) -> Response:
    principal = context.principal
    if principal is None or not principal.tenant_id:
        raise HTTPException(403, "Tenant context is required.")
    try:
        await handler.execute(DeleteCompanyCommand(CompanyIdVO.from_value(company_id)))
    except CompanyNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc
    return Response(status_code=204)
