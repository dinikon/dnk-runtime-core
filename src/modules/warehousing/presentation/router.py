from fastapi import APIRouter

from src.modules.warehousing.presentation.warehouse.router import (
    router as warehouse_router,
)

router = APIRouter(prefix="/warehousing")
router.include_router(warehouse_router)
