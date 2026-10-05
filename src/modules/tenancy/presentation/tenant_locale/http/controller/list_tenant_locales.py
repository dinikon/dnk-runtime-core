from uuid import UUID

from fastapi import HTTPException

from src.modules.identity.presentation.access.depends import AuthorizationServiceDep
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.tenancy.application.tenant_locale.query.list_tenant_locales.query import (
    ListTenantLocalesQuery,
)
from src.modules.tenancy.presentation.tenant_locale.depends import (
    ListTenantLocalesHandlerDep,
)
from src.modules.tenancy.presentation.tenant_locale.http.response.tenant_locale import (
    TenantLocaleResponse,
)


async def list_tenant_locales(
    context: AuthenticatedRequestContextDep,
    handler: ListTenantLocalesHandlerDep,
    authorization: AuthorizationServiceDep,
) -> list[TenantLocaleResponse]:
    """Читает локали текущего tenant."""
    principal = context.principal
    if principal is None or not principal.tenant_id:
        raise HTTPException(403, "Tenant context is required.")
    if not await authorization.can(
        user_id=UUID(principal.user_id),
        tenant_id=UUID(principal.tenant_id),
        action="list",
        resource_type="tenancy.locale",
    ):
        raise HTTPException(403, "Tenant locale listing is not allowed.")
    result = await handler.execute(ListTenantLocalesQuery())
    return [TenantLocaleResponse.from_dto(item) for item in result]
