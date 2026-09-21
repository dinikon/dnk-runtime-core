from src.modules.price_lists.domain.offer.error import OfferNotFoundError
from src.modules.price_lists.domain.price_list.error import PriceListNotFoundError
from src.modules.shared.domain.domain_error import DomainError
from sqlalchemy.exc import OperationalError
from src.modules.price_lists.presentation.http.offer.responses.schemas import (
    OfferResponse,
    OfferStateResponse,
)
from decimal import Decimal
from datetime import datetime
from uuid import UUID
from typing import Literal
from fastapi import APIRouter, Query, HTTPException
from src.modules.shared.presentation.identity_context.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.price_lists.presentation.depends.application import (
    OfferHistoryUseCaseDep,
)
from src.modules.price_lists.application.offer.query.offer_history_query import (
    OfferHistoryQuery,
)
from src.modules.price_lists.domain.offer.value_object import OfferIdVO
from src.modules.price_lists.presentation.http.boundary import (
    context_ids,
)
from src.modules.price_lists.presentation.http.offer.responses.schemas import (
    OffsetOffersResponse,
    CursorOffersResponse,
)

router = APIRouter()


@router.get("/{offer_id}/history")
async def offer_history(
    offer_id: UUID,
    context: AuthenticatedRequestContextDep,
    use_case: OfferHistoryUseCaseDep,
    observed_from: datetime | None = None,
    observed_to: datetime | None = None,
    purchase_price_min: Decimal | None = None,
    purchase_price_max: Decimal | None = None,
    rrp_min: Decimal | None = None,
    rrp_max: Decimal | None = None,
    recommended_retail_income_min: Decimal | None = None,
    recommended_retail_income_max: Decimal | None = None,
    margin_percent_min: Decimal | None = None,
    margin_percent_max: Decimal | None = None,
    quantity_min: int | None = Query(default=None, ge=0),
    quantity_max: int | None = Query(default=None, ge=0),
    availability: list[str] = Query(default=[]),
    change_reason: list[str] = Query(default=[]),
    sort: str = "observed_at",
    direction: Literal["asc", "desc"] = "desc",
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    pagination: Literal["offset", "cursor"] = "offset",
    cursor: str | None = Query(default=None, max_length=4096),
    include_total: bool = False,
):
    """HTTP-запрос offer_history с совместимым offset и cursor режимом."""
    try:
        tenant_id, _ = context_ids(context)
        filters = dict(
            observed_from=observed_from,
            observed_to=observed_to,
            purchase_price_min=purchase_price_min,
            purchase_price_max=purchase_price_max,
            rrp_min=rrp_min,
            rrp_max=rrp_max,
            recommended_retail_income_min=recommended_retail_income_min,
            recommended_retail_income_max=recommended_retail_income_max,
            margin_percent_min=margin_percent_min,
            margin_percent_max=margin_percent_max,
            quantity_min=quantity_min,
            quantity_max=quantity_max,
            availability=availability,
            change_reason=change_reason,
        )
        result = await use_case(
            OfferHistoryQuery(
                tenant_id=tenant_id,
                offer_id=OfferIdVO.from_value(offer_id),
                filters=filters,
                offset=offset,
                limit=limit,
                sort=sort,
                direction=direction,
                pagination=pagination,
                cursor=cursor,
                include_total=include_total,
            )
        )
        items = [OfferStateResponse.from_dto(item) for item in result.items]
        if pagination == "offset":
            return OffsetOffersResponse(
                items=items, total=result.total, offset=offset, limit=limit
            )
        response = CursorOffersResponse(
            items=items,
            limit=limit,
            next_cursor=result.next_cursor,
            has_more=result.has_more,
            total=result.total,
        )
        return response.model_dump(
            mode="json", exclude={"total"} if not include_total else set()
        )
    except (OfferNotFoundError, PriceListNotFoundError) as exc:
        raise HTTPException(404, str(exc)) from exc
    except DomainError as exc:
        raise HTTPException(422, str(exc)) from exc
    except OperationalError as exc:
        raise HTTPException(503, "Offer storage is temporarily unavailable.") from exc


__all__ = ["router"]
