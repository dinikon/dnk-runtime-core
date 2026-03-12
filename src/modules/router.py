from fastapi import APIRouter

from src.modules.crm.presentation.api.router import router as crm_router
from src.modules.identity.presentation.api.router import router as identity_router
from src.modules.tenancy.presentation.api.router import router as tenancy_router

router = APIRouter()
router.include_router(tenancy_router)
router.include_router(identity_router)
router.include_router(crm_router)

__all__ = ["router"]
