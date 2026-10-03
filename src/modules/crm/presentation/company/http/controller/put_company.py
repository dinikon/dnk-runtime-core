from uuid import UUID

from fastapi import HTTPException

from src.modules.crm.application.company.command.update_company.command import (
    UpdateCompanyCommand,
)
from src.modules.crm.domain.company.error import (
    CompanyNotFoundError,
    InvalidCompanyLegalNameError,
)
from src.modules.crm.domain.company.value_object.identifier import CompanyIdVO
from src.modules.crm.presentation.company.depends import UpdateCompanyHandlerDep
from src.modules.crm.presentation.company.http.request.put_company import (
    PutCompanyRequest,
)
from src.modules.crm.presentation.company.http.response.put_company import (
    PutCompanyResponse,
)
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


async def put_company(
    company_id: UUID,
    payload: PutCompanyRequest,
    context: AuthenticatedRequestContextDep,
    handler: UpdateCompanyHandlerDep,
) -> PutCompanyResponse:
    principal = context.principal
    if principal is None or not principal.tenant_id:
        raise HTTPException(403, "Tenant context is required.")
    command = UpdateCompanyCommand(
        company_id=CompanyIdVO.from_value(company_id),
        actor_id=EntityIdVO.from_value(principal.user_id),
        legal_name=payload.legal_name,
    )
    try:
        result = await handler.execute(command)
    except CompanyNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc
    except InvalidCompanyLegalNameError as exc:
        raise HTTPException(422, str(exc)) from exc
    return PutCompanyResponse.from_dto(result)
