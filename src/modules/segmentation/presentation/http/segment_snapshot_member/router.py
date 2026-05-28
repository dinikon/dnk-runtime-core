from fastapi import APIRouter

from src.modules.segmentation.presentation.http.segment_snapshot_member.controllers import (
    list_segment_snapshot_members,
)

router = APIRouter()
router.include_router(list_segment_snapshot_members.router)

__all__ = ["router"]
