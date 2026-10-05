from uuid import UUID

from fastapi import HTTPException

from src.modules.identity.presentation.access.depends import AuthorizationServiceDep
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.tenancy.application.tenant_locale.command.add_tenant_locale.command import (
    AddTenantLocaleCommand,
)
from src.modules.tenancy.domain.tenant_locale.error import (
    InvalidTenantLocaleError,
    TenantLocaleAlreadySelectedError,
)
from src.modules.tenancy.presentation.tenant_locale.depends import (
    AddTenantLocaleHandlerDep,
)
from src.modules.tenancy.presentation.tenant_locale.http.request.add_tenant_locale import (
    AddTenantLocaleRequest,
)
from src.modules.tenancy.presentation.tenant_locale.http.response.tenant_locale import (
    TenantLocaleResponse,
)


async def add_tenant_locale(
    payload: AddTenantLocaleRequest,
    context: AuthenticatedRequestContextDep,
    handler: AddTenantLocaleHandlerDep,
    authorization: AuthorizationServiceDep,
) -> TenantLocaleResponse:
    """Добавляет локаль текущему tenant и переводит доменные ошибки в HTTP."""
    principal = context.principal
    if principal is None or not principal.tenant_id:
        raise HTTPException(403, "Tenant context is required.")
    if not await authorization.can(
        user_id=UUID(principal.user_id),
        tenant_id=UUID(principal.tenant_id),
        action="add",
        resource_type="tenancy.locale",
    ):
        raise HTTPException(403, "Tenant locale modification is not allowed.")
    try:
        result = await handler.execute(
            AddTenantLocaleCommand(
                code=payload.code,
                actor_id=EntityIdVO.from_value(principal.user_id),
            )
        )
    except InvalidTenantLocaleError as exc:
        raise HTTPException(422, str(exc)) from exc
    except TenantLocaleAlreadySelectedError as exc:
        raise HTTPException(409, str(exc)) from exc
    return TenantLocaleResponse.from_dto(result)
