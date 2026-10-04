from uuid import UUID

from fastapi import HTTPException

from src.modules.inventory.application.sku.command.create_sku.command import (
    CreateSkuCommand,
)
from src.modules.inventory.domain.sku.error import (
    InvalidSkuCodeError,
    InvalidSkuTitleError,
    SkuCodeAlreadyExistsError,
    SkuIdentifierAlreadyExistsError,
)
from src.modules.inventory.presentation.sku.depends import CreateSkuHandlerDep
from src.modules.inventory.presentation.sku.http.request.create_sku import (
    CreateSkuRequest,
)
from src.modules.inventory.presentation.sku.http.response.create_sku import (
    CreateSkuResponse,
)
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.identity.presentation.access.depends import AuthorizationServiceDep
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


async def create_sku(
    payload: CreateSkuRequest,
    context: AuthenticatedRequestContextDep,
    handler: CreateSkuHandlerDep,
    authorization: AuthorizationServiceDep,
) -> CreateSkuResponse:
    """Проверяет права, создаёт команду и переводит ожидаемые ошибки в HTTP."""
    principal = context.principal
    if principal is None or not principal.tenant_id:
        raise HTTPException(403, "Tenant context is required.")
    if not await authorization.can(
        user_id=UUID(principal.user_id),
        tenant_id=UUID(principal.tenant_id),
        action="create",
        resource_type="inventory.sku",
    ):
        raise HTTPException(403, "SKU creation is not allowed.")
    try:
        result = await handler.execute(
            CreateSkuCommand(
                actor_id=EntityIdVO.from_value(principal.user_id),
                code=payload.code,
                title=payload.title,
            )
        )
    except (InvalidSkuCodeError, InvalidSkuTitleError) as exc:
        raise HTTPException(422, str(exc)) from exc
    except (SkuCodeAlreadyExistsError, SkuIdentifierAlreadyExistsError) as exc:
        raise HTTPException(409, str(exc)) from exc
    return CreateSkuResponse.from_dto(result)
