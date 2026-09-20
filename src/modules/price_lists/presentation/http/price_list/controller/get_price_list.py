from uuid import UUID
from fastapi import APIRouter
from src.modules.shared.presentation.identity_context.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.price_lists.presentation.depends.application import (
    GetPriceListUseCaseDep,
)
from src.modules.price_lists.application.price_list.query.get_price_list_query import (
    GetPriceListQuery,
)
from src.modules.price_lists.domain.price_list.value_object import PriceListIdVO
from src.modules.price_lists.presentation.http.boundary import (
    context_ids,
    dto_values,
    http_errors,
)
from src.modules.price_lists.presentation.http.price_list.responses.schemas import (
    PriceListResponse,
)

router = APIRouter()


@router.get("/{price_list_id}", response_model=PriceListResponse)
async def get_price_list(
    price_list_id: UUID,
    context: AuthenticatedRequestContextDep,
    use_case: GetPriceListUseCaseDep,
):
    """Возвращает прайс текущего tenant."""
    with http_errors():
        tenant_id, _ = context_ids(context)
        return PriceListResponse(
            **dto_values(
                await use_case(
                    GetPriceListQuery(
                        tenant_id, PriceListIdVO.from_value(price_list_id)
                    )
                )
            )
        )


__all__ = ["router"]
