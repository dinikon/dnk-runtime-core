from datetime import date
from fastapi import APIRouter, HTTPException
from sqlalchemy.exc import OperationalError
from src.modules.currency.application.functional_currency.query.get_functional_currency_query import (
    GetFunctionalCurrencyQuery,
)
from src.modules.currency.domain.functional_currency.error import (
    FunctionalCurrencyNotConfigured,
)
from src.modules.currency.presentation.depends.application import (
    GetFunctionalCurrencyUseCaseDep,
)
from src.modules.currency.presentation.http.authorization import permissions
from src.modules.currency.presentation.http.functional_currency.responses.period_response import (
    FunctionalCurrencyResponse,
)
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.shared.presentation.identity_context.depends import (
    AuthenticatedRequestContextDep,
)

router = APIRouter()


@router.get("/functional-currency", response_model=FunctionalCurrencyResponse)
async def get_functional_currency(
    context: AuthenticatedRequestContextDep,
    use_case: GetFunctionalCurrencyUseCaseDep,
    business_date: date,
):
    """HTTP entrypoint for get functional currency."""
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
        return FunctionalCurrencyResponse(
            currency=str(
                await use_case(GetFunctionalCurrencyQuery(tenant, business_date))
            )
        )
    except FunctionalCurrencyNotConfigured as exc:
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
