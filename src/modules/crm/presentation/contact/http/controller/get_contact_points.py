from uuid import UUID

from fastapi import HTTPException

from src.modules.crm.application.contact.query.list_contact_points.query import (
    ListContactContactPointsQuery,
)
from src.modules.crm.domain.contact.error import ContactNotFoundError
from src.modules.crm.domain.contact.value_object.identifier import ContactIdVO
from src.modules.crm.presentation.contact.depends import (
    ListContactContactPointsHandlerDep,
)
from src.modules.crm.presentation.contact.http.response.get_contact_points import (
    GetContactContactPointsResponse,
)
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


async def get_contact_contact_points(
    contact_id: UUID,
    context: AuthenticatedRequestContextDep,
    handler: ListContactContactPointsHandlerDep,
) -> GetContactContactPointsResponse:
    """Читает контактные данные contact."""
    principal = context.principal
    if principal is None or not principal.tenant_id:
        raise HTTPException(403, "Tenant context is required.")
    tenant_id = EntityIdVO.from_value(principal.tenant_id)
    try:
        result = await handler.execute(
            ListContactContactPointsQuery(tenant_id, ContactIdVO.from_value(contact_id))
        )
    except ContactNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc
    return GetContactContactPointsResponse.from_dto(result)
