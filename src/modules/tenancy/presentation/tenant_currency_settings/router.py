from fastapi import APIRouter, Depends

from src.modules.identity.presentation.auth.depends import (
    require_authenticated_request_context,
)
from src.modules.tenancy.presentation.tenant_currency_settings.http.controller.get_tenant_currency_settings import (
    get_tenant_currency_settings,
)
from src.modules.tenancy.presentation.tenant_currency_settings.http.response.get_tenant_currency_settings import (
    GetTenantCurrencySettingsResponse,
)

router = APIRouter()
router.add_api_route(
    "/current/currency-settings",
    get_tenant_currency_settings,
    methods=["GET"],
    response_model=GetTenantCurrencySettingsResponse,
    dependencies=[Depends(require_authenticated_request_context)],
)
