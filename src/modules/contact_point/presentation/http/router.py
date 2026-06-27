from __future__ import annotations

from fastapi import APIRouter

from src.modules.contact_point.presentation.http.controllers import (
    attach_contact_point_router,
    detach_contact_point_router,
    get_contact_point_router,
    list_contact_point_bindings_router,
    list_contact_points_router,
    list_owner_contact_points_router,
)

router = APIRouter(prefix="/contact-points", tags=["contact-points"])
router.include_router(attach_contact_point_router)
router.include_router(detach_contact_point_router)
router.include_router(list_contact_points_router)
router.include_router(list_contact_point_bindings_router)
router.include_router(list_owner_contact_points_router)
router.include_router(get_contact_point_router)

__all__ = ["router"]
