from fastapi import APIRouter

from src.modules.tenancy.presentation.http.console_tenant.controller.resolve_tenant import (
    router as resolve_tenant_router,
)
from src.modules.tenancy.presentation.tenant_locale.router import (
    router as tenant_locale_router,
)

router = APIRouter(prefix="/tenants", tags=["tenants"])
router.include_router(resolve_tenant_router)
router.include_router(tenant_locale_router)

__all__ = ["router"]
