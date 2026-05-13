from fastapi import APIRouter

from src.modules.communication.presentation.http.provider_connection.controller import (
    create_provider_connection,
    list_provider_connections,
)

router = APIRouter()
router.include_router(create_provider_connection.router)
router.include_router(list_provider_connections.router)

__all__ = ["router"]
