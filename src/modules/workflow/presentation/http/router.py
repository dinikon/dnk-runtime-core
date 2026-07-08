from fastapi import APIRouter

from src.modules.workflow.presentation.http.workflow_application.controller import (
    create_workflow_router,
    list_workflows_router,
    update_workflow_router,
)

router = APIRouter()
router.include_router(create_workflow_router)
router.include_router(list_workflows_router)
router.include_router(update_workflow_router)

__all__ = ["router"]
