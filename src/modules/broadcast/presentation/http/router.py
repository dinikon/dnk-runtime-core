from fastapi import APIRouter

from src.modules.broadcast.presentation.http.broadcast.controller import (
    create_broadcast_router,
    describe_broadcast_fields_router,
    get_broadcast_router,
    list_broadcasts_router,
)

router = APIRouter(prefix="/broadcast", tags=["broadcasts"])
router.include_router(create_broadcast_router)
router.include_router(describe_broadcast_fields_router)
router.include_router(get_broadcast_router)
router.include_router(list_broadcasts_router)

__all__ = ["router"]
