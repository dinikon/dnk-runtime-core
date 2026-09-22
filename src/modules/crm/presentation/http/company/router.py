from fastapi import APIRouter

from src.modules.crm.presentation.http.company.controller import (
    create_company_router,
    delete_company_router,
    get_company_router,
    list_companies_router,
    update_company_router,
)

router = APIRouter()
for action_router in (
    create_company_router,
    list_companies_router,
    get_company_router,
    update_company_router,
    delete_company_router,
):
    router.include_router(action_router, prefix="/companies", tags=["crm-companies"])

__all__ = ["router"]
