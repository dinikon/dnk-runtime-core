from __future__ import annotations

from fastapi import APIRouter

from src.modules.communication.presentation.http.outbound_message.router import (
    _publish_send_job_after_commit,
    router as outbound_message_router,
)
from src.modules.communication.presentation.http.provider_connection.router import (
    router as provider_connection_router,
)
from src.modules.communication.presentation.http.provider_connector.router import (
    router as provider_connector_router,
)
from src.modules.communication.presentation.http.message_template.router import (
    router as message_template_router,
)
from src.modules.communication.presentation.http.delivery.router import (
    router as delivery_router,
)

router = APIRouter()
router.include_router(provider_connector_router)
router.include_router(provider_connection_router)
router.include_router(message_template_router)
router.include_router(outbound_message_router)
router.include_router(delivery_router)

__all__ = ["_publish_send_job_after_commit", "router"]
