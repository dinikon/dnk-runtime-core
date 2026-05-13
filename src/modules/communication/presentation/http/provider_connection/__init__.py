from fastapi import APIRouter

from src.modules.communication.presentation.http.provider_connection.controller import (
    create_provider_connection_router,
    list_provider_connections_router,
)

router = APIRouter()
router.include_router(create_provider_connection_router)
router.include_router(list_provider_connections_router)

__all__ = ["router"]
