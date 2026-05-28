from fastapi import APIRouter

from src.modules.segmentation.presentation.http.segment_snapshot.controllers import (
    create_segment_snapshot,
    get_segment_snapshot,
    list_segment_snapshots,
)

router = APIRouter()
router.include_router(create_segment_snapshot.router)
router.include_router(list_segment_snapshots.router)
router.include_router(get_segment_snapshot.router)

__all__ = ["router"]
