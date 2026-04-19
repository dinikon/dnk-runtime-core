from fastapi import APIRouter

from src.modules.tenancy.presentation.http.admin_tenant.controller import (
    create_tenant_router,
)
from src.modules.tenancy.presentation.http.console_tenant.controller import (
    resolve_tenant_router,
)

router = APIRouter()
router.include_router(create_tenant_router)
router.include_router(resolve_tenant_router)

__all__ = ["router"]
