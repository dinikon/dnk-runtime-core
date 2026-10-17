from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError

from src.modules.crm.application.company.command.create_company.command import (
    CreateCompanyCommand,
)
from src.modules.crm.domain.company.error import InvalidCompanyLegalNameError
from src.modules.crm.presentation.company.depends import CreateCompanyHandlerDep
from src.modules.crm.presentation.company.http.request.create_company import (
    CreateCompanyRequest,
)
from src.modules.crm.presentation.company.http.response.create_company import (
    CreateCompanyResponse,
)
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


async def create_company(
    payload: CreateCompanyRequest,
    context: AuthenticatedRequestContextDep,
    handler: CreateCompanyHandlerDep,
) -> CreateCompanyResponse:
    principal = context.principal
    if principal is None or not principal.tenant_id:
        raise HTTPException(403, "Tenant context is required.")
    command = CreateCompanyCommand(
        actor_id=EntityIdVO.from_value(principal.user_id),
        legal_name=payload.legal_name,
    )
    try:
        result = await handler.execute(command)
    except InvalidCompanyLegalNameError as exc:
        raise HTTPException(422, str(exc)) from exc
    except IntegrityError as exc:
        if (
            getattr(exc.orig, "sqlstate", None) == "23505"
            and getattr(exc.orig.__cause__, "constraint_name", None) == "pk_companies"
        ):
            raise HTTPException(409, "Company identifier already exists.") from exc
        raise
    return CreateCompanyResponse.from_dto(result)
