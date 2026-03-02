from fastapi import APIRouter

from src.presentation.api.admin_tenants import router as admin_tenants_router

router = APIRouter()
router.include_router(admin_tenants_router)

__all__ = ["router"]
