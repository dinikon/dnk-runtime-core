from fastapi import APIRouter, HTTPException
from sqlalchemy.exc import OperationalError
from src.modules.currency.application.settings.query.get_currency_settings_query import (
    GetCurrencySettingsQuery,
)
from src.modules.currency.presentation.depends.application import (
    GetCurrencySettingsUseCaseDep,
)
from src.modules.currency.presentation.http.authorization import permissions
from src.modules.currency.presentation.http.settings.responses.settings_response import (
    SettingsResponse,
    PolicyResponse,
    PeriodResponse,
    ProviderStatusResponse,
)
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.shared.presentation.identity_context.depends import (
    AuthenticatedRequestContextDep,
)

router = APIRouter()


@router.get("/settings", response_model=SettingsResponse)
async def get_settings(
    context: AuthenticatedRequestContextDep, use_case: GetCurrencySettingsUseCaseDep
):
    """HTTP entrypoint for get settings."""
    if "currency.view" not in permissions(context):
        raise HTTPException(
            403,
            {
                "code": "currency_forbidden",
                "message": "Currency permission is required.",
            },
        )
    tenant = EntityIdVO.from_value(context.principal.tenant_id)
    try:
        r = await use_case(GetCurrencySettingsQuery(tenant))
        return SettingsResponse(
            configured=r.configured,
            policy=PolicyResponse.from_dto(r.policy) if r.policy else None,
            enabled_currencies=[str(c) for c in r.enabled_currencies],
            periods=[PeriodResponse.from_dto(p) for p in r.periods],
            functional_currency=(
                str(r.functional_currency) if r.functional_currency else None
            ),
            future_functional_currency=(
                str(r.future_functional_currency)
                if r.future_functional_currency
                else None
            ),
            business_date=r.business_date,
            provider_status=ProviderStatusResponse.from_dto(r.provider_status),
            permissions=permissions(context),
            default_display_currency=(
                str(r.default_display_currency) if r.default_display_currency else None
            ),
            next_business_day_at=r.next_business_day_at,
        )
    except OperationalError as exc:
        raise HTTPException(
            503,
            {
                "code": "currency_storage_unavailable",
                "message": "Currency storage is temporarily unavailable.",
            },
        ) from exc


__all__ = ["router"]
