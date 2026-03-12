from fastapi import APIRouter

from src.modules.crm.presentation.api.contacts import (
    router as contacts_router,
)

router = APIRouter()
router.include_router(contacts_router)

__all__ = ["router"]
