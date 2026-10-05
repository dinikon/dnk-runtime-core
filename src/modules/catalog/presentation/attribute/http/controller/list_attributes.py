from uuid import UUID

from fastapi import HTTPException

from src.modules.catalog.application.attribute.query.list_attributes.query import (
    ListAttributesQuery,
)
from src.modules.catalog.domain.attribute.error import InvalidAttributeLocaleError
from src.modules.catalog.domain.attribute.locale import AttributeLocaleVO
from src.modules.catalog.presentation.attribute.depends import ListAttributesHandlerDep
from src.modules.catalog.presentation.attribute.http.response.list_attributes import (
    ListAttributesResponse,
)
from src.modules.identity.presentation.access.depends import AuthorizationServiceDep
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)


async def list_attributes(
    locale: str,
    context: AuthenticatedRequestContextDep,
    handler: ListAttributesHandlerDep,
    authorization: AuthorizationServiceDep,
) -> ListAttributesResponse:
    principal = context.principal
    if principal is None or not principal.tenant_id:
        raise HTTPException(403, "Tenant context is required.")
    if not await authorization.can(
        user_id=UUID(principal.user_id),
        tenant_id=UUID(principal.tenant_id),
        action="read",
        resource_type="catalog.attribute",
    ):
        raise HTTPException(403, "Attribute reading is not allowed.")
    try:
        items = await handler.execute(ListAttributesQuery(AttributeLocaleVO(locale)))
    except InvalidAttributeLocaleError as exc:
        raise HTTPException(422, str(exc)) from exc
    return ListAttributesResponse.from_dtos(items)
