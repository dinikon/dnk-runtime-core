from fastapi import APIRouter
from src.modules.currency.presentation.http.manual_rate.controller.set_manual_rate import (
    router as set_manual_rate_router,
)

router = APIRouter()
router.include_router(set_manual_rate_router)

__all__ = ["router"]
