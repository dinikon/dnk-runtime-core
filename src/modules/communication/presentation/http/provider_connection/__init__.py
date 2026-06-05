from fastapi import APIRouter

from src.modules.communication.presentation.http.provider_connection.controller import (
    create_provider_connection,
    delete_provider_connection,
    list_provider_connections,
    update_provider_connection_status,
)

router = APIRouter()
router.include_router(create_provider_connection.router)
router.include_router(delete_provider_connection.router)
router.include_router(list_provider_connections.router)
router.include_router(update_provider_connection_status.router)

__all__ = ["router"]
