from src.modules.segmentation.presentation.http import (
    segment_definition,
    segment_snapshot,
    segment_snapshot_member,
    segment_static_member,
    segment_version,
)

router = segment_definition.router
router.include_router(segment_version.router)
router.include_router(segment_static_member.router)
router.include_router(segment_snapshot.router)
router.include_router(segment_snapshot_member.router)

__all__ = ["router"]
