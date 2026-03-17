from fastapi import APIRouter

from src.modules.crm.presentation.http.router import router as crm_router
from src.modules.identity.presentation.api.router import router as identity_router
from src.modules.runtime_record.presentation.http.router import (
    router as runtime_record_router,
)
from src.modules.runtime_schema.presentation.http.router import (
    router as runtime_schema_router,
)
from src.modules.tenancy.presentation.http.router import router as tenancy_router

router = APIRouter(prefix="/api")

router.include_router(tenancy_router)
router.include_router(identity_router, prefix="/console/auth")
router.include_router(crm_router)
router.include_router(runtime_schema_router)
router.include_router(runtime_record_router)

__all__ = ["router"]
