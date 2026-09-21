from fastapi import APIRouter
from src.modules.currency.presentation.http.exchange_rate.controller.get_rate_history import (
    router as get_rate_history_router,
)
from src.modules.currency.presentation.http.exchange_rate.controller.resolve_quote import (
    router as resolve_quote_router,
)

router = APIRouter()
router.include_router(get_rate_history_router)
router.include_router(resolve_quote_router)

__all__ = ["router"]
