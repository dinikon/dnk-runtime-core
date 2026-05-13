from fastapi import APIRouter

from src.modules.communication.presentation.http.template.controller import (
    activate_template_version_router,
    create_message_template_router,
    create_template_version_router,
    list_message_templates_router,
)

router = APIRouter()
router.include_router(create_message_template_router)
router.include_router(create_template_version_router)
router.include_router(activate_template_version_router)
router.include_router(list_message_templates_router)

__all__ = ["router"]
