from fastapi import APIRouter

router = APIRouter()
list_router = APIRouter()
from src.modules.price_lists.presentation.http.offer.controller.list_all_offers import (
    router as list_all_offers_router,
)

router.include_router(list_all_offers_router, prefix="/price-list-offers")
from src.modules.price_lists.presentation.http.offer.controller.list_price_list_offers import (
    router as list_price_list_offers_router,
)

list_router.include_router(list_price_list_offers_router, prefix="/price-lists")
from src.modules.price_lists.presentation.http.offer.controller.offer_history import (
    router as offer_history_router,
)

router.include_router(offer_history_router, prefix="/price-list-offers")

__all__ = ["router", "list_router"]
