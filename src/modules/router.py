from fastapi import APIRouter


from src.modules.identity.presentation.api.router import router as identity_router
from src.modules.tenancy.presentation.api.router import router as tenancy_router
from src.modules.universal_access.presentation.http.router import (
    router as universal_access_router,
)

router = APIRouter()
router.include_router(tenancy_router)
router.include_router(identity_router)
router.include_router(universal_access_router)


__all__ = ["router"]
