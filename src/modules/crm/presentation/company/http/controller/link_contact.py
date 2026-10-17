from uuid import UUID

from fastapi import HTTPException, Response

from src.modules.crm.application.contact.command.link_company.command import (
    LinkCompanyCommand,
)
from src.modules.crm.domain.company.error import CompanyNotFoundError
from src.modules.crm.domain.company.value_object.identifier import CompanyIdVO
from src.modules.crm.domain.contact.error import ContactNotFoundError
from src.modules.crm.domain.contact.value_object.identifier import ContactIdVO
from src.modules.crm.presentation.depends.company_link import LinkCompanyHandlerDep
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)


async def link_contact(
    company_id: UUID,
    contact_id: UUID,
    context: AuthenticatedRequestContextDep,
    handler: LinkCompanyHandlerDep,
) -> Response:
    principal = context.principal
    if principal is None or not principal.tenant_id:
        raise HTTPException(403, "Tenant context is required.")
    command = LinkCompanyCommand(
        ContactIdVO.from_value(contact_id), CompanyIdVO.from_value(company_id)
    )
    try:
        await handler.execute(command)
    except (ContactNotFoundError, CompanyNotFoundError) as exc:
        raise HTTPException(404, str(exc)) from exc
    return Response(status_code=204)
