from fastapi import APIRouter
from src.modules.currency.presentation.http.functional_currency.controller.get_functional_currency import (
    router as get_functional_currency_router,
)
from src.modules.currency.presentation.http.functional_currency.controller.list_periods import (
    router as list_periods_router,
)
from src.modules.currency.presentation.http.functional_currency.controller.schedule_period import (
    router as schedule_period_router,
)

router = APIRouter()
router.include_router(get_functional_currency_router)
router.include_router(list_periods_router)
router.include_router(schedule_period_router)

__all__ = ["router"]
