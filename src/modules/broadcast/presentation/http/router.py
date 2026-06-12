from fastapi import APIRouter

from src.modules.broadcast.presentation.http.broadcast.controller import (
    create_broadcast_router,
)

router = APIRouter(prefix="/broadcast", tags=["broadcasts"])
router.include_router(create_broadcast_router)

__all__ = ["router"]
