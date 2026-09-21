from fastapi import APIRouter
from src.modules.currency.presentation.http.settings.controller.get_settings import (
    router as get_settings_router,
)
from src.modules.currency.presentation.http.settings.controller.initialize_currency import (
    router as initialize_currency_router,
)

router = APIRouter()
router.include_router(get_settings_router)
router.include_router(initialize_currency_router)

__all__ = ["router"]
