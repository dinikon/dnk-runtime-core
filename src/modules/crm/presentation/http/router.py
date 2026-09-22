from fastapi import APIRouter

from src.modules.crm.presentation.http.company import router as company_router
from src.modules.crm.presentation.http.contact import router as contact_router

router = APIRouter(prefix="/crm")
router.include_router(contact_router)
router.include_router(company_router)

__all__ = ["router"]
