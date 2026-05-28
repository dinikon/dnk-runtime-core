from fastapi import APIRouter

from src.modules.segmentation.presentation.http.segment_version.controllers import (
    activate_segment_version,
    create_segment_version,
    get_segment_version,
    list_segment_versions,
    preview_segment_config,
    preview_segment_version,
)

router = APIRouter()
router.include_router(preview_segment_config.router)
router.include_router(create_segment_version.router)
router.include_router(list_segment_versions.router)
router.include_router(get_segment_version.router)
router.include_router(activate_segment_version.router)
router.include_router(preview_segment_version.router)

__all__ = ["router"]
