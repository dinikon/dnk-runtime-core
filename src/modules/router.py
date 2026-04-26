from fastapi import APIRouter

from src.modules.crm.presentation.http.router import router as crm_router
from src.modules.identity.presentation.http.router import router as identity_router
from src.modules.inventory.presentation.http.router import router as inventory_router

from src.modules.tenancy.presentation.http.router import router as tenancy_router

router = APIRouter(prefix="/api")

router.include_router(tenancy_router)
router.include_router(crm_router)
router.include_router(inventory_router)
router.include_router(identity_router, prefix="/console/auth")

__all__ = ["router"]
