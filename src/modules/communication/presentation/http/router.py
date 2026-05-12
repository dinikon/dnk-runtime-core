from __future__ import annotations

from fastapi import APIRouter

from src.modules.communication.presentation.http.message.router import (
    _publish_send_job_after_commit,
    router as message_router,
)
from src.modules.communication.presentation.http.provider.router import (
    router as provider_router,
)
from src.modules.communication.presentation.http.template.router import (
    router as template_router,
)
from src.modules.communication.presentation.http.webhook.router import (
    router as webhook_router,
)

router = APIRouter()
router.include_router(provider_router)
router.include_router(template_router)
router.include_router(message_router)
router.include_router(webhook_router)

__all__ = ["_publish_send_job_after_commit", "router"]
