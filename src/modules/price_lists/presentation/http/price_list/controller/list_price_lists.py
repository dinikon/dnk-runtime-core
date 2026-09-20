from typing import Literal
from fastapi import APIRouter
from src.modules.shared.presentation.identity_context.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.price_lists.presentation.depends.application import (
    ListPriceListsUseCaseDep,
)
from src.modules.price_lists.application.price_list.query.list_price_lists_query import (
    ListPriceListsQuery,
)
from src.modules.price_lists.presentation.http.boundary import (
    context_ids,
    dto_values,
    http_errors,
)
from src.modules.price_lists.presentation.http.price_list.responses.schemas import (
    PriceListListItemResponse,
)

router = APIRouter()


@router.get("")
async def list_price_lists(
    context: AuthenticatedRequestContextDep,
    use_case: ListPriceListsUseCaseDep,
    scope: Literal["current", "archived", "all"] = "current",
):
    """Возвращает список прайсов текущего tenant."""
    with http_errors():
        tenant_id, _ = context_ids(context)
        return {
            "items": [
                PriceListListItemResponse(**dto_values(item))
                for item in await use_case(ListPriceListsQuery(tenant_id, scope))
            ]
        }


__all__ = ["router"]
