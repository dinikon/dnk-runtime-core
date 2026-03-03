from fastapi import APIRouter

from src.modules.tenancy.presentation.api.router import router as tenancy_router

router = APIRouter()
router.include_router(tenancy_router)

__all__ = ["router"]
