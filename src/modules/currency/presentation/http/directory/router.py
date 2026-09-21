from fastapi import APIRouter
from src.modules.currency.presentation.http.directory.controller.list_currencies import (
    router as list_currencies_router,
)

router = APIRouter()
router.include_router(list_currencies_router)

__all__ = ["router"]
