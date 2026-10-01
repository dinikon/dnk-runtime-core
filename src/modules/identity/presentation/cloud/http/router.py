from fastapi import APIRouter
from src.modules.identity.presentation.cloud.http.controller.cloud_callback import (
    cloud_router as cloud_callback_router,
)
from src.modules.identity.presentation.cloud.http.controller.cloud_start import (
    cloud_router as cloud_start_router,
)
from src.modules.identity.presentation.cloud.http.controller.cloud_status import (
    cloud_router as cloud_status_router,
)
from src.modules.identity.presentation.cloud.http.controller.cloud_unlink import (
    cloud_router as cloud_unlink_router,
)

router = APIRouter()
router.include_router(cloud_status_router)
router.include_router(cloud_start_router)
router.include_router(cloud_callback_router)
router.include_router(cloud_unlink_router)
