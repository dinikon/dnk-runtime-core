from fastapi import APIRouter
from src.modules.identity.presentation.cloud.http.controller.cloud_callback import (
    cloud_router as cloud_callback_router,
)
from src.modules.identity.presentation.cloud.http.controller.cloud_start import (
    cloud_start,
)
from fastapi import Depends
from src.modules.identity.presentation.auth.http.csrf import require_csrf
from src.modules.identity.presentation.cloud.http.response.cloud_start import (
    CloudStartResponse,
)
from src.modules.identity.presentation.cloud.http.controller.cloud_status import (
    cloud_router as cloud_status_router,
)
from src.modules.identity.presentation.cloud.http.controller.cloud_unlink import (
    cloud_router as cloud_unlink_router,
)

router = APIRouter()
router.include_router(cloud_status_router)
router.add_api_route(
    "/api/auth/cloud/start/",
    cloud_start,
    methods=["POST"],
    response_model=CloudStartResponse,
    tags=["cloud-auth"],
    dependencies=[Depends(require_csrf)],
)
router.include_router(cloud_callback_router)
router.include_router(cloud_unlink_router)
