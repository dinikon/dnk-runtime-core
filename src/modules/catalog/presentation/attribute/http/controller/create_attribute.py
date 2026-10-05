from uuid import UUID

from fastapi import HTTPException

from src.modules.catalog.application.attribute.command.create_attribute.command import (
    CreateAttributeCommand,
    CreateAttributeContent,
    CreateAttributeOption,
)
from src.modules.catalog.domain.attribute.error import (
    AttributeAlreadyExistsError,
    AttributeLocaleUnavailableError,
    InvalidAttributeError,
    InvalidAttributeLocaleError,
)
from src.modules.catalog.presentation.attribute.depends import CreateAttributeHandlerDep
from src.modules.catalog.presentation.attribute.http.request.create_attribute import (
    CreateAttributeRequest,
)
from src.modules.catalog.presentation.attribute.http.response.create_attribute import (
    CreateAttributeResponse,
)
from src.modules.identity.presentation.access.depends import AuthorizationServiceDep
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


async def create_attribute(
    payload: CreateAttributeRequest,
    context: AuthenticatedRequestContextDep,
    handler: CreateAttributeHandlerDep,
    authorization: AuthorizationServiceDep,
) -> CreateAttributeResponse:
    principal = context.principal
    if principal is None or not principal.tenant_id:
        raise HTTPException(403, "Tenant context is required.")
    if not await authorization.can(
        user_id=UUID(principal.user_id),
        tenant_id=UUID(principal.tenant_id),
        action="create",
        resource_type="catalog.attribute",
    ):
        raise HTTPException(403, "Attribute creation is not allowed.")
    try:
        result = await handler.execute(
            CreateAttributeCommand(
                actor_id=EntityIdVO.from_value(principal.user_id),
                code=payload.code,
                options=tuple(
                    CreateAttributeOption(
                        code=item.code,
                        contents=tuple(
                            CreateAttributeContent(
                                locale=content.locale, name=content.name
                            )
                            for content in item.contents
                        ),
                    )
                    for item in payload.options
                ),
                contents=tuple(
                    CreateAttributeContent(locale=item.locale, name=item.name)
                    for item in payload.contents
                ),
            )
        )
    except (
        InvalidAttributeError,
        InvalidAttributeLocaleError,
        AttributeLocaleUnavailableError,
    ) as exc:
        raise HTTPException(422, str(exc)) from exc
    except AttributeAlreadyExistsError as exc:
        raise HTTPException(409, str(exc)) from exc
    return CreateAttributeResponse.from_dto(result)
