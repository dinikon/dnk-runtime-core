from uuid import UUID

from fastapi import HTTPException

from src.modules.crm.application.company.command.sync_contact_points.command import (
    SyncCompanyContactPointsCommand,
)
from src.modules.crm.application.contact_point.dto import ContactPointDraftDTO
from src.modules.crm.presentation.contact_point.http_errors import (
    contact_point_http_errors,
)
from src.modules.crm.domain.company.error import CompanyNotFoundError
from src.modules.crm.domain.company.value_object.identifier import CompanyIdVO
from src.modules.crm.presentation.company.depends import (
    SyncCompanyContactPointsHandlerDep,
)
from src.modules.crm.presentation.company.http.request.patch_contact_points import (
    PatchCompanyContactPointsRequest,
)
from src.modules.crm.presentation.company.http.response.patch_contact_points import (
    PatchCompanyContactPointsResponse,
)
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


async def patch_company_contact_points(
    company_id: UUID,
    payload: PatchCompanyContactPointsRequest,
    context: AuthenticatedRequestContextDep,
    handler: SyncCompanyContactPointsHandlerDep,
) -> PatchCompanyContactPointsResponse:
    """Изменяет контактные данные company."""
    principal = context.principal
    if principal is None or not principal.tenant_id:
        raise HTTPException(403, "Tenant context is required.")
    tenant_id = EntityIdVO.from_value(principal.tenant_id)
    try:
        with contact_point_http_errors():
            result = await handler.execute(
                SyncCompanyContactPointsCommand(
                    tenant_id=tenant_id,
                    actor_id=EntityIdVO.from_value(principal.user_id),
                    company_id=CompanyIdVO.from_value(company_id),
                    phones=(
                        tuple(
                            ContactPointDraftDTO(**item.model_dump())
                            for item in payload.phones
                        )
                        if payload.phones is not None
                        else None
                    ),
                    emails=(
                        tuple(
                            ContactPointDraftDTO(**item.model_dump())
                            for item in payload.emails
                        )
                        if payload.emails is not None
                        else None
                    ),
                )
            )
    except CompanyNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc
    return PatchCompanyContactPointsResponse.from_dto(result)
