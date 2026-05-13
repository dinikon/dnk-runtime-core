from fastapi import APIRouter

from src.modules.communication.presentation.http.message_template.controller import (
    activate_template_version,
    create_message_template,
    create_template_version,
    list_message_templates,
)

router = APIRouter()
router.include_router(create_message_template.router)
router.include_router(create_template_version.router)
router.include_router(activate_template_version.router)
router.include_router(list_message_templates.router)

__all__ = ["router"]
