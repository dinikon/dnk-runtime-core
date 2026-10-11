from fastapi import HTTPException

from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.tenancy.application.tenant_currency_settings.query.get_tenant_currency_settings.query import (
    GetTenantCurrencySettingsQuery,
)
from src.modules.tenancy.domain.tenant_currency_settings.error import (
    TenantCurrencySettingsNotFoundError,
)
from src.modules.tenancy.domain.tenant.value_object.tenant_id import TenantIdVO
from src.modules.tenancy.presentation.tenant_currency_settings.depends import (
    GetTenantCurrencySettingsHandlerDep,
)
from src.modules.tenancy.presentation.tenant_currency_settings.http.response.get_tenant_currency_settings import (
    GetTenantCurrencySettingsResponse,
)


async def get_tenant_currency_settings(
    context: AuthenticatedRequestContextDep,
    handler: GetTenantCurrencySettingsHandlerDep,
) -> GetTenantCurrencySettingsResponse:
    """Читает настройку Tenant только из доверенного контекста Identity."""
    if context.principal is None or context.principal.tenant_id is None:
        raise HTTPException(403, "Tenant context required.")
    query = GetTenantCurrencySettingsQuery(
        tenant_id=TenantIdVO.from_value(context.principal.tenant_id)
    )
    try:
        result = await handler.execute(query)
    except TenantCurrencySettingsNotFoundError as exc:
        raise HTTPException(404, "Tenant currency settings not found.") from exc
    return GetTenantCurrencySettingsResponse(base_currency=result.base_currency)
