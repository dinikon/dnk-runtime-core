from fastapi import APIRouter

from src.modules.tenancy.presentation.http.admin_tenants import (
    router as admin_tenants_router,
)
from src.modules.tenancy.presentation.http.console_tenants import (
    router as console_tenants_router,
)

router = APIRouter()
router.include_router(admin_tenants_router)
router.include_router(console_tenants_router)

__all__ = ["router"]
