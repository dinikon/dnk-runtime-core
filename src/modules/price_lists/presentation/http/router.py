from fastapi import APIRouter
from src.modules.price_lists.presentation.http.price_list.router import (
    router as price_router,
)
from src.modules.price_lists.presentation.http.offer.router import (
    router as offer_router,
    list_router,
)
from src.modules.price_lists.presentation.http.sync_run.router import (
    router as run_router,
)

router = APIRouter(tags=["price-lists"])
router.include_router(price_router)
router.include_router(list_router)
router.include_router(run_router)
offers_router = APIRouter(tags=["price-list-offers"])
offers_router.include_router(offer_router)

__all__ = ["router", "offers_router"]
