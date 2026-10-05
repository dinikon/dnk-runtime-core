from fastapi import APIRouter

from src.modules.reference_data.presentation.country.router import (
    router as country_router,
)
from src.modules.reference_data.presentation.currency.router import (
    router as currency_router,
)
from src.modules.reference_data.presentation.locale.router import (
    router as locale_router,
)
from src.modules.reference_data.presentation.time_zone.router import (
    router as time_zone_router,
)

router = APIRouter(prefix="/reference-data")
router.include_router(country_router)
router.include_router(currency_router)
router.include_router(locale_router)
router.include_router(time_zone_router)
