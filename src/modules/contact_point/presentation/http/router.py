from __future__ import annotations

from fastapi import APIRouter

from src.modules.contact_point.presentation.http.controllers import (
    attach_contact_point_router,
    detach_contact_point_router,
    list_owner_contact_points_router,
)

router = APIRouter()
router.include_router(attach_contact_point_router)
router.include_router(detach_contact_point_router)
router.include_router(list_owner_contact_points_router)

__all__ = ["router"]
