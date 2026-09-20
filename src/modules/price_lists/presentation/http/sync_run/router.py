from fastapi import APIRouter

router = APIRouter()
from src.modules.price_lists.presentation.http.sync_run.controller.list_runs import (
    router as list_runs_router,
)

router.include_router(list_runs_router, prefix="/price-lists")

__all__ = ["router"]
