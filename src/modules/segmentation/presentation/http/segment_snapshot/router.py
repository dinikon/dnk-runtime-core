from fastapi import APIRouter

from src.modules.segmentation.presentation.http.segment_snapshot import controllers

router = APIRouter()
for controller_router in controllers.routers:
    router.include_router(controller_router)

__all__ = ["router"]
