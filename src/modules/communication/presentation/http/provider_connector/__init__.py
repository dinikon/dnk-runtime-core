from fastapi import APIRouter

from src.modules.communication.presentation.http.provider_connector.controller import (
    import_provider_connector_yaml_router,
    list_provider_connectors_router,
)

router = APIRouter()
router.include_router(import_provider_connector_yaml_router)
router.include_router(list_provider_connectors_router)

__all__ = ["router"]
