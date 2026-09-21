from fastapi import APIRouter
from src.modules.currency.presentation.http.conversion.controller.convert_money import (
    router as convert_money_router,
)

router = APIRouter()
router.include_router(convert_money_router)

__all__ = ["router"]
