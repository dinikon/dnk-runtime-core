from fastapi import APIRouter
from src.modules.currency.presentation.http.conversion.router import (
    router as conversion_router,
)
from src.modules.currency.presentation.http.directory.router import (
    router as directory_router,
)
from src.modules.currency.presentation.http.enabled_currency.router import (
    router as enabled_currency_router,
)
from src.modules.currency.presentation.http.exchange_rate.router import (
    router as exchange_rate_router,
)
from src.modules.currency.presentation.http.functional_currency.router import (
    router as functional_currency_router,
)
from src.modules.currency.presentation.http.manual_rate.router import (
    router as manual_rate_router,
)
from src.modules.currency.presentation.http.policy.router import router as policy_router
from src.modules.currency.presentation.http.provider.router import (
    router as provider_router,
)
from src.modules.currency.presentation.http.settings.router import (
    router as settings_router,
)

router = APIRouter(prefix="/currency", tags=["Currency"])
router.include_router(directory_router)
router.include_router(settings_router)
router.include_router(policy_router)
router.include_router(enabled_currency_router)
router.include_router(functional_currency_router)
router.include_router(manual_rate_router)
router.include_router(exchange_rate_router)
router.include_router(conversion_router)
router.include_router(provider_router)

__all__ = ["router"]
