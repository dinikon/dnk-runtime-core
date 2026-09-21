from decimal import Decimal
from fastapi import APIRouter, HTTPException
from sqlalchemy.exc import OperationalError
from src.modules.currency.application.conversion.command.convert_money_command import (
    ConvertMoneyCommand,
)
from src.modules.currency.application.conversion.dto.conversion_request import (
    ConversionRequest,
)
from src.modules.currency.domain.conversion.error import CurrencyPrecisionUndefined
from src.modules.currency.domain.conversion.value_object.conversion_purpose import (
    ConversionPurpose,
)
from src.modules.currency.domain.directory.error import CurrencyNotFound
from src.modules.currency.domain.enabled_currency.error import CurrencyDisabled
from src.modules.currency.domain.exchange_rate.error import (
    ExchangeRateNotFound,
    CrossRateUnavailable,
)
from src.modules.currency.domain.functional_currency.error import (
    FunctionalCurrencyNotConfigured,
)
from src.modules.currency.domain.policy.error import CurrencyPolicyNotConfigured
from src.modules.currency.presentation.depends.application import (
    ConvertMoneyUseCaseDep,
    ConvertToFunctionalCurrencyUseCaseDep,
)
from src.modules.currency.presentation.http.authorization import permissions
from src.modules.currency.presentation.http.conversion.requests.convert_request import (
    ConvertRequest,
)
from src.modules.currency.presentation.http.conversion.responses.converted_money_response import (
    ConvertedMoneyResponse,
)
from src.modules.shared.domain.value_object.currency import CurrencyCodeVO as Code
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.shared.domain.value_object.money import Money
from src.modules.shared.domain.value_object.money_errors import (
    InvalidCurrencyCodeError,
    InvalidMoneyError,
    CurrencyMismatchError,
)
from src.modules.shared.presentation.identity_context.depends import (
    AuthenticatedRequestContextDep,
)

router = APIRouter()


@router.post("/convert", response_model=ConvertedMoneyResponse)
async def convert_money(
    context: AuthenticatedRequestContextDep,
    use_case: ConvertMoneyUseCaseDep,
    functional_use_case: ConvertToFunctionalCurrencyUseCaseDep,
    payload: ConvertRequest,
):
    """HTTP entrypoint for convert money."""
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
        money = Money(Decimal(payload.amount), Code(payload.source_currency))
        if payload.target_currency:
            r = await use_case(
                ConvertMoneyCommand(
                    tenant,
                    ConversionRequest(
                        money,
                        payload.business_date,
                        Code(payload.target_currency),
                        ConversionPurpose(payload.purpose),
                        payload.precision,
                    ),
                )
            )
        else:
            r = await functional_use_case(
                ConvertMoneyCommand(
                    tenant,
                    ConversionRequest(
                        money,
                        payload.business_date,
                        None,
                        ConversionPurpose(payload.purpose),
                        payload.precision,
                    ),
                )
            )
        return ConvertedMoneyResponse.from_dto(r)
    except CurrencyNotFound as exc:
        raise HTTPException(404, {"code": exc.code, "message": str(exc)}) from exc
    except CurrencyDisabled as exc:
        raise HTTPException(422, {"code": exc.code, "message": str(exc)}) from exc
    except CurrencyPolicyNotConfigured as exc:
        raise HTTPException(422, {"code": exc.code, "message": str(exc)}) from exc
    except FunctionalCurrencyNotConfigured as exc:
        raise HTTPException(422, {"code": exc.code, "message": str(exc)}) from exc
    except CrossRateUnavailable as exc:
        raise HTTPException(422, {"code": exc.code, "message": str(exc)}) from exc
    except ExchangeRateNotFound as exc:
        raise HTTPException(422, {"code": exc.code, "message": str(exc)}) from exc
    except CurrencyPrecisionUndefined as exc:
        raise HTTPException(422, {"code": exc.code, "message": str(exc)}) from exc
    except InvalidCurrencyCodeError as exc:
        raise HTTPException(422, {"code": exc.code, "message": str(exc)}) from exc
    except InvalidMoneyError as exc:
        raise HTTPException(422, {"code": exc.code, "message": str(exc)}) from exc
    except CurrencyMismatchError as exc:
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
