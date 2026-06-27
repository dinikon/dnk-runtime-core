from fastapi import APIRouter

from src.modules.workflow.presentation.http.workflow_application.controller import (
    create_workflow_router,
)

router = APIRouter()
router.include_router(create_workflow_router)

__all__ = ["router"]
