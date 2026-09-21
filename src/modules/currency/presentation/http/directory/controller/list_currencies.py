from fastapi import APIRouter, HTTPException
from sqlalchemy.exc import OperationalError
from src.modules.currency.application.directory.query.list_currencies_query import (
    ListCurrenciesQuery,
)
from src.modules.currency.presentation.depends.application import (
    ListCurrenciesUseCaseDep,
)
from src.modules.currency.presentation.http.authorization import permissions
from src.modules.currency.presentation.http.directory.responses.currency_response import (
    CurrencyResponse,
)
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.shared.presentation.identity_context.depends import (
    AuthenticatedRequestContextDep,
)

router = APIRouter()


@router.get("/directory", response_model=list[CurrencyResponse])
async def list_currencies(
    context: AuthenticatedRequestContextDep, use_case: ListCurrenciesUseCaseDep
):
    """HTTP entrypoint for list currencies."""
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
            CurrencyResponse.from_dto(i) for i in await use_case(ListCurrenciesQuery())
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
