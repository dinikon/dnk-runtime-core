from fastapi import APIRouter

from src.modules.segmentation.presentation.http.segment_static_member.controllers import (
    add_static_member,
    list_static_members,
    remove_static_member,
)

router = APIRouter()
router.include_router(add_static_member.router)
router.include_router(list_static_members.router)
router.include_router(remove_static_member.router)

__all__ = ["router"]
