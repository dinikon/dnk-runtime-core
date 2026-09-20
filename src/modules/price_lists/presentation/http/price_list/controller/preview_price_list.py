from uuid import UUID
from fastapi import APIRouter, Depends
from src.modules.identity.presentation.http.csrf import require_csrf
from src.modules.shared.presentation.identity_context.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.price_lists.presentation.depends.application import (
    PreviewPriceListUseCaseDep,
)
from src.modules.price_lists.application.price_list.query.preview_price_list_query import (
    PreviewPriceListQuery,
)
from src.modules.price_lists.domain.price_list.value_object import PriceListIdVO
from src.modules.price_lists.presentation.http.boundary import (
    context_ids,
    dto_values,
    http_errors,
)
from src.modules.price_lists.presentation.http.price_list.responses.schemas import (
    PreviewResponse,
)
from src.modules.price_lists.presentation.http.price_list.requests.preview_price_list_request import (
    PreviewPriceListRequest,
)

router = APIRouter()


@router.post(
    "/{price_list_id}/preview",
    dependencies=[Depends(require_csrf)],
    response_model=PreviewResponse,
)
async def preview_price_list(
    price_list_id: UUID,
    context: AuthenticatedRequestContextDep,
    use_case: PreviewPriceListUseCaseDep,
    payload: PreviewPriceListRequest | None = None,
):
    """Показывает ограниченную выборку источника без записи предложений."""
    with http_errors():
        tenant_id, _ = context_ids(context)
        candidate = (
            payload.model_dump(exclude_unset=True, mode="json") if payload else {}
        )
        return PreviewResponse(
            **dto_values(
                await use_case(
                    PreviewPriceListQuery(
                        tenant_id, PriceListIdVO.from_value(price_list_id), candidate
                    )
                )
            )
        )


__all__ = ["router"]
