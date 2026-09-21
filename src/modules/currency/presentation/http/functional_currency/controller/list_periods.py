from fastapi import APIRouter, HTTPException
from sqlalchemy.exc import OperationalError
from src.modules.currency.application.functional_currency.query.list_functional_currency_periods_query import (
    ListFunctionalCurrencyPeriodsQuery,
)
from src.modules.currency.presentation.depends.application import (
    ListFunctionalCurrencyPeriodsUseCaseDep,
)
from src.modules.currency.presentation.http.authorization import permissions
from src.modules.currency.presentation.http.functional_currency.responses.period_response import (
    PeriodResponse,
)
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.shared.presentation.identity_context.depends import (
    AuthenticatedRequestContextDep,
)

router = APIRouter()


@router.get("/periods", response_model=list[PeriodResponse])
async def list_periods(
    context: AuthenticatedRequestContextDep,
    use_case: ListFunctionalCurrencyPeriodsUseCaseDep,
):
    """HTTP entrypoint for list periods."""
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
        return [
            PeriodResponse.from_dto(p)
            for p in await use_case(ListFunctionalCurrencyPeriodsQuery(tenant))
        ]
    except OperationalError as exc:
        raise HTTPException(
            503,
            {
                "code": "currency_storage_unavailable",
                "message": "Currency storage is temporarily unavailable.",
            },
        ) from exc


__all__ = ["router"]
