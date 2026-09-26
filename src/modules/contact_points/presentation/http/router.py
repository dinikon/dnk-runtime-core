from fastapi import APIRouter
from src.modules.contact_points.presentation.http.label.controller.list_labels import (
    router as list_router,
)
from src.modules.contact_points.presentation.http.label.controller.create_label import (
    router as create_router,
)
from src.modules.contact_points.presentation.http.label.controller.update_label import (
    router as update_router,
)

router = APIRouter(prefix="/contact-points", tags=["contact-point-labels"])
router.include_router(list_router, prefix="/labels")
router.include_router(create_router, prefix="/labels")
router.include_router(update_router, prefix="/labels")

__all__ = ["router"]
