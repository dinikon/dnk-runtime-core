from fastapi import APIRouter

from src.modules.tenancy.presentation.http.console_tenant.controller import (
    resolve_tenant_router,
)

router = APIRouter(prefix="/tenants", tags=["tenants"])
router.include_router(resolve_tenant_router)

__all__ = ["router"]
