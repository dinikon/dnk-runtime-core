from typing import Annotated

from fastapi import Depends, HTTPException

from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.tenancy.domain.tenant.value_object.tenant_id import TenantIdVO

from src.modules.shared.presentation.persistence.depends import UoWDep
from src.modules.tenancy.application.tenant_currency_settings.query.get_tenant_currency_settings.handler import (
    GetTenantCurrencySettingsHandler,
)
from src.modules.tenancy.infrastructure.tenant_currency_settings.persistence.query_repository import (
    SqlAlchemyTenantCurrencySettingsQueryRepository,
)


def get_tenant_currency_settings_handler(
    uow: UoWDep,
    context: AuthenticatedRequestContextDep,
) -> GetTenantCurrencySettingsHandler:
    """Собирает публичный сценарий чтения на сессии общего HTTP UoW."""
    if context.principal is None or context.principal.tenant_id is None:
        raise HTTPException(403, "Tenant context required.")
    tenant_id = TenantIdVO.from_value(context.principal.tenant_id)
    return GetTenantCurrencySettingsHandler(
        SqlAlchemyTenantCurrencySettingsQueryRepository(uow.session, tenant_id)
    )


GetTenantCurrencySettingsHandlerDep = Annotated[
    GetTenantCurrencySettingsHandler, Depends(get_tenant_currency_settings_handler)
]
