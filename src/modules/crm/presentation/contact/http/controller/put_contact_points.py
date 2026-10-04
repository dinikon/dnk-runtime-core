from uuid import UUID

from fastapi import HTTPException

from src.modules.crm.application.contact.command.sync_contact_points.command import (
    SyncContactContactPointsCommand,
)
from src.modules.crm.application.contact_point.dto import ContactPointDraftDTO
from src.modules.crm.presentation.contact_point.http_errors import (
    contact_point_http_errors,
)
from src.modules.crm.domain.contact.error import ContactNotFoundError
from src.modules.crm.domain.contact.value_object.identifier import ContactIdVO
from src.modules.crm.presentation.contact.depends import (
    SyncContactContactPointsHandlerDep,
)
from src.modules.crm.presentation.contact.http.request.put_contact_points import (
    PutContactContactPointsRequest,
)
from src.modules.crm.presentation.contact.http.response.put_contact_points import (
    PutContactContactPointsResponse,
)
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


async def put_contact_contact_points(
    contact_id: UUID,
    payload: PutContactContactPointsRequest,
    context: AuthenticatedRequestContextDep,
    handler: SyncContactContactPointsHandlerDep,
) -> PutContactContactPointsResponse:
    """Изменяет контактные данные contact."""
    principal = context.principal
    if principal is None or not principal.tenant_id:
        raise HTTPException(403, "Tenant context is required.")
    tenant_id = EntityIdVO.from_value(principal.tenant_id)
    try:
        with contact_point_http_errors():
            result = await handler.execute(
                SyncContactContactPointsCommand(
                    tenant_id=tenant_id,
                    actor_id=EntityIdVO.from_value(principal.user_id),
                    contact_id=ContactIdVO.from_value(contact_id),
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
    except ContactNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc
    return PutContactContactPointsResponse.from_dto(result)
