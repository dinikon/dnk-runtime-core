from fastapi import APIRouter

from src.modules.broadcast.presentation.http.router import router as broadcast_router
from src.modules.contact_point.presentation.http.router import (
    router as contact_point_router,
)
from src.modules.custom_object.presentation.http.router import (
    router as custom_object_router,
)
from src.modules.communication.presentation.http.router import (
    router as communication_router,
)
from src.modules.crm.presentation.http.router import router as crm_router
from src.modules.identity.presentation.http.router import router as identity_router
from src.modules.inventory.presentation.http.router import router as inventory_router
from src.modules.schema_registry.presentation.http.router import (
    router as schema_registry_router,
)
from src.modules.segmentation.presentation.http.router import (
    router as segmentation_router,
)

from src.modules.tenancy.presentation.http.router import router as tenancy_router

router = APIRouter(prefix="/api/console")

router.include_router(tenancy_router)
router.include_router(broadcast_router)
router.include_router(crm_router)
router.include_router(inventory_router)
router.include_router(schema_registry_router)
router.include_router(custom_object_router)
router.include_router(communication_router)
router.include_router(segmentation_router)
router.include_router(contact_point_router)
router.include_router(identity_router)

__all__ = ["router"]
