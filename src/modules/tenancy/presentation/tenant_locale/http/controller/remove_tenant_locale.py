from uuid import UUID

from fastapi import HTTPException

from src.modules.identity.presentation.access.depends import AuthorizationServiceDep
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.tenancy.application.tenant_locale.command.remove_tenant_locale.command import (
    RemoveTenantLocaleCommand,
)
from src.modules.tenancy.domain.tenant_locale.error import (
    InvalidTenantLocaleError,
    TenantLocaleNotSelectedError,
)
from src.modules.tenancy.presentation.tenant_locale.depends import (
    RemoveTenantLocaleHandlerDep,
)


async def remove_tenant_locale(
    code: str,
    context: AuthenticatedRequestContextDep,
    handler: RemoveTenantLocaleHandlerDep,
    authorization: AuthorizationServiceDep,
) -> None:
    """Удаляет выбор локали текущего tenant."""
    principal = context.principal
    if principal is None or not principal.tenant_id:
        raise HTTPException(403, "Tenant context is required.")
    if not await authorization.can(
        user_id=UUID(principal.user_id),
        tenant_id=UUID(principal.tenant_id),
        action="remove",
        resource_type="tenancy.locale",
    ):
        raise HTTPException(403, "Tenant locale modification is not allowed.")
    try:
        await handler.execute(RemoveTenantLocaleCommand(code))
    except InvalidTenantLocaleError as exc:
        raise HTTPException(422, str(exc)) from exc
    except TenantLocaleNotSelectedError as exc:
        raise HTTPException(404, str(exc)) from exc
