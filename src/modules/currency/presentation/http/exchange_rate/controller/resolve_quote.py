from datetime import date
from fastapi import APIRouter, HTTPException
from sqlalchemy.exc import OperationalError
from src.modules.currency.application.exchange_rate.query.resolve_exchange_rate_query import (
    ResolveExchangeRateQuery,
)
from src.modules.currency.domain.directory.error import CurrencyNotFound
from src.modules.currency.domain.enabled_currency.error import CurrencyDisabled
from src.modules.currency.domain.exchange_rate.error import (
    ExchangeRateNotFound,
    CrossRateUnavailable,
)
from src.modules.currency.domain.policy.error import CurrencyPolicyNotConfigured
from src.modules.currency.presentation.depends.application import (
    ResolveExchangeRateUseCaseDep,
)
from src.modules.currency.presentation.http.authorization import permissions
from src.modules.currency.presentation.http.exchange_rate.responses.quote_response import (
    QuoteResponse,
)
from src.modules.shared.domain.value_object.currency import CurrencyCodeVO as Code
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.shared.domain.value_object.money_errors import InvalidCurrencyCodeError
from src.modules.shared.presentation.identity_context.depends import (
    AuthenticatedRequestContextDep,
)

router = APIRouter()


@router.get("/quote", response_model=QuoteResponse)
async def resolve_quote(
    context: AuthenticatedRequestContextDep,
    use_case: ResolveExchangeRateUseCaseDep,
    source: str,
    target: str,
    business_date: date,
):
    """HTTP entrypoint for resolve quote."""
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
        return QuoteResponse.from_dto(
            await use_case(
                ResolveExchangeRateQuery(
                    tenant, Code(source), Code(target), business_date
                )
            )
        )
    except CurrencyNotFound as exc:
        raise HTTPException(404, {"code": exc.code, "message": str(exc)}) from exc
    except CurrencyDisabled as exc:
        raise HTTPException(422, {"code": exc.code, "message": str(exc)}) from exc
    except CurrencyPolicyNotConfigured as exc:
        raise HTTPException(422, {"code": exc.code, "message": str(exc)}) from exc
    except CrossRateUnavailable as exc:
        raise HTTPException(422, {"code": exc.code, "message": str(exc)}) from exc
    except ExchangeRateNotFound as exc:
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
