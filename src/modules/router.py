from fastapi import APIRouter

from src.modules.identity.presentation.http.router import router as identity_router

from src.modules.tenancy.presentation.http.router import router as tenancy_router

router = APIRouter(prefix="/api/console")

router.include_router(tenancy_router)
router.include_router(identity_router)

__all__ = ["router"]
