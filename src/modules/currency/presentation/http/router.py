from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, Query

from src.modules.identity.presentation.http.csrf import require_csrf
from src.modules.shared.presentation.identity_context.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.shared.domain.value_object.money import Money
from src.modules.shared.domain.value_object.currency import CurrencyCodeVO as Code
from src.modules.currency.application.settings.query.get_currency_settings_query import (
    GetCurrencySettingsQuery,
)
from src.modules.currency.application.commands import (
    InitializeCurrency,
    ConfigureCurrencyPolicy,
    SetEnabledCurrency,
    ScheduleFunctionalCurrencyChange,
    SetManualRate,
)
from src.modules.currency.domain.models import (
    CurrencyPolicy,
    ProviderCode,
    RateDatePolicy,
    RoundingMode,
    CurrencyPair,
    ConversionPurpose,
)
from src.modules.currency.domain.errors import (
    CurrencyPolicyNotConfigured,
    CurrencyError,
)
from src.modules.currency.presentation.depends import CurrencyServicesDep
from .schemas import (
    InitializeRequest,
    ConfigureRequest,
    EnabledRequest,
    ScheduleRequest,
    RateRequest,
    ConvertRequest,
    ActionResponse,
    SettingsResponse,
    ConvertedMoneyResponse,
)
from .boundary import require, permissions, wire, currency_errors

router = APIRouter(prefix="/currency", tags=["Currency"])
write = [Depends(require_csrf)]


def policy_from(payload, version=1):
    return CurrencyPolicy(
        Code(payload.default_transaction_currency),
        ProviderCode(payload.provider_code),
        RateDatePolicy(payload.rate_date_policy),
        RoundingMode(payload.rounding_mode),
        payload.allow_cross_rate,
        Code(payload.bridge_currency),
        payload.business_timezone,
        version,
    )


@router.get("/directory")
async def directory(
    context: AuthenticatedRequestContextDep, services: CurrencyServicesDep
):
    require(context, "currency.view")
    return wire(await services.directory.list_active())


@router.get("/settings", response_model=SettingsResponse)
async def settings(
    context: AuthenticatedRequestContextDep, services: CurrencyServicesDep
):
    tenant, _ = require(context, "currency.view")
    with currency_errors():
        result = await services.get_settings(GetCurrencySettingsQuery(tenant))
        return {**wire(result), "permissions": permissions(context)}


@router.post(
    "/initialize", dependencies=write, response_model=ActionResponse, status_code=201
)
async def initialize(
    payload: InitializeRequest,
    context: AuthenticatedRequestContextDep,
    services: CurrencyServicesDep,
):
    tenant, actor = require(context, "currency.manage_policy")
    with currency_errors():
        await services.settings.initialize(
            InitializeCurrency(
                tenant,
                actor,
                policy_from(payload),
                tuple(Code(c) for c in payload.enabled_currencies),
                Code(payload.functional_currency),
                payload.valid_from,
                payload.reason,
            )
        )
    return ActionResponse()


@router.put("/policy", dependencies=write)
async def configure(
    payload: ConfigureRequest,
    context: AuthenticatedRequestContextDep,
    services: CurrencyServicesDep,
):
    tenant, actor = require(context, "currency.manage_policy")
    with currency_errors():
        return wire(
            await services.settings.configure(
                ConfigureCurrencyPolicy(
                    tenant, actor, policy_from(payload), payload.expected_version
                )
            )
        )


@router.put("/enabled/{code}", dependencies=write, response_model=ActionResponse)
async def enable(
    code: str,
    payload: EnabledRequest,
    context: AuthenticatedRequestContextDep,
    services: CurrencyServicesDep,
):
    tenant, actor = require(context, "currency.manage_enabled")
    with currency_errors():
        await services.settings.set_enabled(
            SetEnabledCurrency(tenant, actor, Code(code), payload.enabled)
        )
    return ActionResponse()


@router.get("/functional-currency")
async def functional(
    business_date: date,
    context: AuthenticatedRequestContextDep,
    services: CurrencyServicesDep,
):
    tenant, _ = require(context, "currency.view")
    with currency_errors():
        return {
            "currency": str(
                await services.facade.get_functional_currency(
                    tenant_id=tenant, business_date=business_date
                )
            )
        }


@router.get("/periods")
async def periods(
    context: AuthenticatedRequestContextDep, services: CurrencyServicesDep
):
    tenant, _ = require(context, "currency.view")
    return wire(await services.periods.list_periods(tenant_id=tenant))


@router.post("/periods", dependencies=write, status_code=201)
async def schedule(
    payload: ScheduleRequest,
    context: AuthenticatedRequestContextDep,
    services: CurrencyServicesDep,
):
    tenant, actor = require(context, "currency.change_functional_currency")
    with currency_errors():
        return wire(
            await services.settings.schedule(
                ScheduleFunctionalCurrencyChange(
                    tenant,
                    actor,
                    Code(payload.currency),
                    payload.effective_from,
                    payload.reason,
                )
            )
        )


@router.post("/rates/manual", dependencies=write, status_code=201)
async def manual(
    payload: RateRequest,
    context: AuthenticatedRequestContextDep,
    services: CurrencyServicesDep,
):
    tenant, actor = require(context, "currency.manage_rates")
    with currency_errors():
        return wire(
            await services.settings.set_manual_rate(
                SetManualRate(
                    tenant,
                    actor,
                    CurrencyPair(
                        Code(payload.source_currency), Code(payload.target_currency)
                    ),
                    Decimal(payload.rate),
                    payload.effective_date,
                )
            )
        )


@router.get("/rates")
async def rates(
    context: AuthenticatedRequestContextDep,
    services: CurrencyServicesDep,
    provider: str = "NBU",
    source: str | None = None,
    target: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
):
    tenant, _ = require(context, "currency.view")
    with currency_errors():
        if bool(source) != bool(target):
            raise CurrencyError("Specify both source and target currencies.")
        return wire(
            await services.rates.history(
                tenant_id=tenant,
                provider=ProviderCode(provider),
                pair=CurrencyPair(Code(source), Code(target)) if source else None,
                limit=limit,
                offset=offset,
            )
        )


@router.get("/quote")
async def quote(
    source: str,
    target: str,
    business_date: date,
    context: AuthenticatedRequestContextDep,
    services: CurrencyServicesDep,
):
    tenant, _ = require(context, "currency.view")
    with currency_errors():
        return wire(
            await services.facade.resolve_rate(
                tenant_id=tenant,
                source=Code(source),
                target=Code(target),
                date=business_date,
            )
        )


@router.post("/convert", response_model=ConvertedMoneyResponse)
async def convert(
    payload: ConvertRequest,
    context: AuthenticatedRequestContextDep,
    services: CurrencyServicesDep,
):
    tenant, _ = require(context, "currency.view")
    with currency_errors():
        values = dict(
            tenant_id=tenant,
            money=Money(Decimal(payload.amount), Code(payload.source_currency)),
            purpose=ConversionPurpose(payload.purpose),
        )
        if payload.target_currency:
            result = await services.facade.convert(
                target=Code(payload.target_currency),
                date=payload.business_date,
                **values,
            )
        else:
            result = await services.facade.convert_to_functional(
                business_date=payload.business_date, **values
            )
        return wire(result)
