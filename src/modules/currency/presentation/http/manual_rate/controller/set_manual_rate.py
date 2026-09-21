from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.exc import OperationalError
from uuid import uuid4
from src.modules.currency.application.manual_rate.command.set_manual_rate_command import (
    SetManualRate,
)
from src.modules.currency.domain.directory.error import CurrencyNotFound
from src.modules.currency.domain.enabled_currency.error import CurrencyDisabled
from src.modules.currency.domain.exchange_rate.error import InvalidExchangeRate
from src.modules.currency.domain.exchange_rate.value_object.currency_pair import (
    CurrencyPair,
)
from src.modules.currency.domain.manual_rate.value_object.id import (
    ManualExchangeRateIdVO,
)
from src.modules.currency.domain.policy.error import (
    CurrencyConflict,
    CurrencyPolicyNotConfigured,
)
from src.modules.currency.presentation.depends.application import (
    SetManualRateUseCaseDep,
)
from src.modules.currency.presentation.http.authorization import permissions
from src.modules.currency.presentation.http.exchange_rate.responses.rate_response import (
    RateResponse,
)
from src.modules.currency.presentation.http.manual_rate.requests.rate_request import (
    RateRequest,
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
    "/rates/manual",
    dependencies=[Depends(require_csrf)],
    status_code=201,
    response_model=RateResponse,
)
async def set_manual_rate(
    context: AuthenticatedRequestContextDep,
    use_case: SetManualRateUseCaseDep,
    payload: RateRequest,
    response: Response,
):
    """HTTP entrypoint for set manual rate."""
    if "currency.manage_rates" not in permissions(context):
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
        identifier = ManualExchangeRateIdVO(uuid4())
        r = await use_case(
            SetManualRate(
                tenant,
                actor,
                CurrencyPair(
                    Code(payload.source_currency), Code(payload.target_currency)
                ),
                Decimal(payload.rate),
                payload.effective_date,
                identifier,
            )
        )
        response.status_code = 201 if r.created else 200
        return RateResponse.from_dto(r.rate)
    except CurrencyNotFound as exc:
        raise HTTPException(404, {"code": exc.code, "message": str(exc)}) from exc
    except CurrencyConflict as exc:
        raise HTTPException(409, {"code": exc.code, "message": str(exc)}) from exc
    except CurrencyDisabled as exc:
        raise HTTPException(422, {"code": exc.code, "message": str(exc)}) from exc
    except CurrencyPolicyNotConfigured as exc:
        raise HTTPException(422, {"code": exc.code, "message": str(exc)}) from exc
    except InvalidExchangeRate as exc:
        raise HTTPException(422, {"code": exc.code, "message": str(exc)}) from exc
    except InvalidCurrencyCodeError as exc:
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
