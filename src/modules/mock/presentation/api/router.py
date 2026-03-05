from fastapi import APIRouter

from src.modules.mock.presentation.api.workplaces import (
    router as mock_workplaces_router,
)

router = APIRouter()
router.include_router(mock_workplaces_router)

__all__ = ["router"]
