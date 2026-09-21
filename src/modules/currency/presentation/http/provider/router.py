from fastapi import APIRouter
from src.modules.currency.presentation.http.provider.controller.get_provider_status import (
    router as get_provider_status_router,
)
from src.modules.currency.presentation.http.provider.controller.list_rate_sources import (
    router as sources_router,
)

router = APIRouter()
router.include_router(get_provider_status_router)

__all__ = ["router"]

router.include_router(sources_router)
