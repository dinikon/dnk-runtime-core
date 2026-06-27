from fastapi import APIRouter

from src.modules.communication.presentation.http.provider_connector.controller import (
    delete_provider_connector,
    import_provider_connector_yaml,
    list_provider_connectors,
    update_provider_connector_status,
)

router = APIRouter()
router.include_router(delete_provider_connector.router)
router.include_router(import_provider_connector_yaml.router)
router.include_router(list_provider_connectors.router)
router.include_router(update_provider_connector_status.router)

__all__ = ["router"]
