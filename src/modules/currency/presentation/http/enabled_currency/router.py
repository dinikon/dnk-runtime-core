from fastapi import APIRouter
from src.modules.currency.presentation.http.enabled_currency.controller.set_enabled_currency import (
    router as set_enabled_currency_router,
)

router = APIRouter()
router.include_router(set_enabled_currency_router)

__all__ = ["router"]
