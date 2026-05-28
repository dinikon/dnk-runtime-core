from fastapi import APIRouter

from src.modules.segmentation.presentation.http.segment_definition.controllers import (
    archive_segment_definition,
    create_segment_definition,
    get_segment_definition,
    list_segment_definitions,
    preview_segment_definition,
    update_segment_definition,
)

router = APIRouter()
router.include_router(create_segment_definition.router)
router.include_router(list_segment_definitions.router)
router.include_router(preview_segment_definition.router)
router.include_router(get_segment_definition.router)
router.include_router(update_segment_definition.router)
router.include_router(archive_segment_definition.router)

__all__ = ["router"]
