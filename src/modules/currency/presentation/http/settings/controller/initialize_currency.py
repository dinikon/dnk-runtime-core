from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import OperationalError
from uuid import uuid4
from src.modules.currency.application.settings.command.initialize_currency_command import (
    InitializeCurrency,
)
from src.modules.currency.domain.directory.error import CurrencyNotFound
from src.modules.currency.domain.enabled_currency.error import CurrencyDisabled
from src.modules.currency.domain.error import CurrencyError
from src.modules.currency.domain.functional_currency.error import (
    FunctionalCurrencyPeriodOverlap,
)
from src.modules.currency.domain.functional_currency.value_object.id import (
    FunctionalCurrencyPeriodIdVO,
)
from src.modules.currency.domain.policy.entity import CurrencyPolicy
from src.modules.currency.domain.policy.error import CurrencyConflict
from src.modules.currency.domain.policy.value_object.rate_date_policy import (
    RateDatePolicy,
)
from src.modules.currency.domain.policy.value_object.rounding_mode import RoundingMode
from src.modules.currency.domain.provider.value_object.provider_code import ProviderCode
from src.modules.currency.presentation.depends.application import (
    InitializeCurrencyUseCaseDep,
)
from src.modules.currency.presentation.http.authorization import permissions
from src.modules.currency.presentation.http.settings.requests.initialize_request import (
    InitializeRequest,
)
from src.modules.currency.presentation.http.settings.responses.settings_response import (
    ActionResponse,
)
from src.modules.identity.presentation.http.csrf import require_csrf
from src.modules.shared.domain.value_object.currency import CurrencyCodeVO as Code
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.shared.domain.value_object.money_errors import InvalidCurrencyCodeError
from src.modules.shared.presentation.identity_context.depends import (
    AuthenticatedRequestContextDep,
)

router = APIRouter()


@router.post(
    "/initialize",
    dependencies=[Depends(require_csrf)],
    status_code=201,
    response_model=ActionResponse,
)
async def initialize_currency(
    context: AuthenticatedRequestContextDep,
    use_case: InitializeCurrencyUseCaseDep,
    payload: InitializeRequest,
):
    """HTTP entrypoint for initialize currency."""
    if "currency.manage_policy" not in permissions(context):
        raise HTTPException(
            403,
            {
                "code": "currency_forbidden",
                "message": "Currency permission is required.",
            },
        )
    tenant = EntityIdVO.from_value(context.principal.tenant_id)
    actor = EntityIdVO.from_value(context.principal.user_id)
    try:
        await use_case(
            InitializeCurrency(
                tenant,
                actor,
                CurrencyPolicy(
                    Code(payload.default_transaction_currency),
                    ProviderCode(payload.provider_code),
                    RateDatePolicy(payload.rate_date_policy),
                    RoundingMode(payload.rounding_mode),
                    payload.allow_cross_rate,
                    Code(payload.bridge_currency),
                    payload.business_timezone,
                    1,
                    (
                        Code(payload.default_display_currency)
                        if payload.default_display_currency
                        else None
                    ),
                ),
                tuple(Code(c) for c in payload.enabled_currencies),
                Code(payload.functional_currency),
                payload.valid_from,
                payload.reason,
                FunctionalCurrencyPeriodIdVO(uuid4()),
            )
        )
        return ActionResponse()
    except CurrencyNotFound as exc:
        raise HTTPException(404, {"code": exc.code, "message": str(exc)}) from exc
    except CurrencyConflict as exc:
        raise HTTPException(409, {"code": exc.code, "message": str(exc)}) from exc
    except FunctionalCurrencyPeriodOverlap as exc:
        raise HTTPException(409, {"code": exc.code, "message": str(exc)}) from exc
    except CurrencyDisabled as exc:
        raise HTTPException(422, {"code": exc.code, "message": str(exc)}) from exc
    except InvalidCurrencyCodeError as exc:
        raise HTTPException(422, {"code": exc.code, "message": str(exc)}) from exc
    except CurrencyError as exc:
        raise HTTPException(422, {"code": exc.code, "message": str(exc)}) from exc
    except OperationalError as exc:
        raise HTTPException(
            503,
            {
                "code": "currency_storage_unavailable",
                "message": "Currency storage is temporarily unavailable.",
            },
        ) from exc


__all__ = ["router"]
