from fastapi import APIRouter

from src.modules.identity.presentation.http.router import router as identity_router
from src.modules.price_lists.presentation.http.router import (
    offers_router as price_list_offers_router,
)
from src.modules.price_lists.presentation.http.router import (
    router as price_lists_router,
)

from src.modules.tenancy.presentation.http.router import router as tenancy_router
from src.modules.currency.presentation.http.router import router as currency_router

router = APIRouter(prefix="/api/console")

router.include_router(tenancy_router)
router.include_router(identity_router)
router.include_router(price_lists_router)
router.include_router(price_list_offers_router)
router.include_router(currency_router)

__all__ = ["router"]
