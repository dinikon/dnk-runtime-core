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
from src.modules.crm.presentation.company.http.request.patch_company import (
    PatchCompanyRequest,
)
from src.modules.crm.presentation.company.http.response.patch_company import (
    PatchCompanyResponse,
)
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


async def patch_company(
    company_id: UUID,
    payload: PatchCompanyRequest,
    context: AuthenticatedRequestContextDep,
    handler: UpdateCompanyHandlerDep,
) -> PatchCompanyResponse:
    principal = context.principal
    if principal is None or not principal.tenant_id:
        raise HTTPException(403, "Tenant context is required.")
    # PatchCompanyRequest отклоняет отсутствие поля и null до вызова контроллера.
    assert payload.legal_name is not None
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
    return PatchCompanyResponse.from_dto(result)
