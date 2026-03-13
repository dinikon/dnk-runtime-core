from fastapi import APIRouter


from src.modules.identity.presentation.api.router import router as identity_router
from src.modules.tenancy.presentation.api.router import router as tenancy_router

router = APIRouter()
router.include_router(tenancy_router)
router.include_router(identity_router)

__all__ = ["router"]
