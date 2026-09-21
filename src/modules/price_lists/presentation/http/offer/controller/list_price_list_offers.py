from src.modules.price_lists.domain.offer.error import OfferNotFoundError
from src.modules.price_lists.domain.price_list.error import PriceListNotFoundError
from src.modules.shared.domain.domain_error import DomainError
from sqlalchemy.exc import OperationalError
from src.modules.price_lists.presentation.http.offer.responses.schemas import (
    OfferResponse,
    OfferStateResponse,
)
from datetime import date
from uuid import UUID
from typing import Literal
from fastapi import APIRouter, Query, HTTPException
from src.modules.shared.presentation.identity_context.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.price_lists.presentation.depends.application import (
    ListOffersUseCaseDep,
)
from src.modules.price_lists.application.offer.query.list_offers_query import (
    ListOffersQuery,
)
from src.modules.price_lists.domain.price_list.value_object import PriceListIdVO
from src.modules.price_lists.presentation.http.boundary import (
    context_ids,
)
from src.modules.price_lists.presentation.http.offer.responses.schemas import (
    OffsetOffersResponse,
    CursorOffersResponse,
)

router = APIRouter()


@router.get("/{price_list_id}/offers")
async def list_price_list_offers(
    price_list_id: UUID,
    context: AuthenticatedRequestContextDep,
    use_case: ListOffersUseCaseDep,
    q: str | None = None,
    sort: str = "observed_at",
    direction: Literal["asc", "desc"] = "desc",
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    include_archived: bool = False,
    pagination: Literal["offset", "cursor"] = "offset",
    cursor: str | None = Query(default=None, max_length=4096),
    include_total: bool = False,
    business_date: date | None = None,
):
    """HTTP-запрос list_price_list_offers с совместимым offset и cursor режимом."""
    try:
        tenant_id, _ = context_ids(context)
        filters = dict(price_list_ids=[PriceListIdVO.from_value(price_list_id)], q=q)
        result = await use_case(
            ListOffersQuery(
                tenant_id=tenant_id,
                include_archived=include_archived,
                filters=filters,
                offset=offset,
                limit=limit,
                sort=sort,
                direction=direction,
                pagination=pagination,
                cursor=cursor,
                include_total=include_total,
                business_date=business_date,
            )
        )
        items = [OfferResponse.from_dto(item) for item in result.items]
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
