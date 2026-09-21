from fastapi import APIRouter, HTTPException, Query
from sqlalchemy.exc import OperationalError
from src.modules.currency.application.exchange_rate.query.get_rate_history_query import (
    GetRateHistoryQuery,
)
from src.modules.currency.domain.error import CurrencyError
from src.modules.currency.domain.exchange_rate.error import InvalidExchangeRate
from src.modules.currency.domain.exchange_rate.value_object.currency_pair import (
    CurrencyPair,
)
from src.modules.currency.domain.provider.value_object.provider_code import ProviderCode
from src.modules.currency.presentation.depends.application import (
    GetRateHistoryUseCaseDep,
)
from src.modules.currency.presentation.http.authorization import permissions
from src.modules.currency.presentation.http.exchange_rate.responses.rate_response import (
    RateResponse,
)
from src.modules.shared.domain.value_object.currency import CurrencyCodeVO as Code
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.shared.domain.value_object.money_errors import InvalidCurrencyCodeError
from src.modules.shared.presentation.identity_context.depends import (
    AuthenticatedRequestContextDep,
)

router = APIRouter()


@router.get("/rates", response_model=list[RateResponse])
async def get_rate_history(
    context: AuthenticatedRequestContextDep,
    use_case: GetRateHistoryUseCaseDep,
    provider: str = "NBU",
    source: str | None = None,
    target: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
):
    """HTTP entrypoint for get rate history."""
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
        if bool(source) != bool(target):
            raise InvalidExchangeRate("Specify both source and target currencies.")
        return [
            RateResponse.from_dto(r)
            for r in await use_case(
                GetRateHistoryQuery(
                    tenant,
                    ProviderCode(provider),
                    CurrencyPair(Code(source), Code(target)) if source else None,
                    limit,
                    offset,
                )
            )
        ]
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
