from fastapi import APIRouter

from src.modules.custom_object.presentation.http.custom_objects import (
    router as custom_objects_router,
)

router = APIRouter()
router.include_router(custom_objects_router)

__all__ = ["router"]
