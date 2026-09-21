from fastapi import APIRouter
from src.modules.currency.presentation.http.policy.controller.configure_policy import (
    router as configure_policy_router,
)

router = APIRouter()
router.include_router(configure_policy_router)

__all__ = ["router"]
