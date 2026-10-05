from uuid import UUID

from fastapi import HTTPException

from src.modules.catalog.application.attribute.query.get_attribute.query import (
    GetAttributeQuery,
)
from src.modules.catalog.domain.attribute.error import (
    AttributeNotFoundError,
    InvalidAttributeLocaleError,
)
from src.modules.catalog.domain.attribute.locale import AttributeLocaleVO
from src.modules.catalog.presentation.attribute.depends import GetAttributeHandlerDep
from src.modules.catalog.presentation.attribute.http.response.get_attribute import (
    GetAttributeResponse,
)
from src.modules.identity.presentation.access.depends import AuthorizationServiceDep
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


async def get_attribute(
    attribute_id: UUID,
    locale: str,
    context: AuthenticatedRequestContextDep,
    handler: GetAttributeHandlerDep,
    authorization: AuthorizationServiceDep,
) -> GetAttributeResponse:
    principal = context.principal
    if principal is None or not principal.tenant_id:
        raise HTTPException(403, "Tenant context is required.")
    if not await authorization.can(
        user_id=UUID(principal.user_id),
        tenant_id=UUID(principal.tenant_id),
        action="read",
        resource_type="catalog.attribute",
        resource_id=attribute_id,
    ):
        raise HTTPException(403, "Attribute reading is not allowed.")
    try:
        result = await handler.execute(
            GetAttributeQuery(
                EntityIdVO.from_value(attribute_id), AttributeLocaleVO(locale)
            )
        )
    except InvalidAttributeLocaleError as exc:
        raise HTTPException(422, str(exc)) from exc
    except AttributeNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc
    return GetAttributeResponse.from_dto(result)
