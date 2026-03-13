from fastapi import APIRouter

from src.modules.crm.presentation.http.router import router as crm_router

from src.modules.identity.presentation.api.router import router as identity_router
from src.modules.tenancy.presentation.api.router import router as tenancy_router
from src.modules.universal_access.presentation.http.router import (
    router as universal_access_router,
)

router = APIRouter(prefix="/api")

router.include_router(tenancy_router)
router.include_router(identity_router, prefix="/console/auth")
router.include_router(crm_router, prefix="/console/crm")
router.include_router(universal_access_router, prefix="/console/universal-access")


__all__ = ["router"]
