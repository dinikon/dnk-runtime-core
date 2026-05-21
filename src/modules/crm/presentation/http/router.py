from fastapi import APIRouter

from src.modules.crm.presentation.http.company.controller import (
    create_company_router,
    delete_company_router,
    describe_company_fields_router,
    get_company_router,
    list_companies_router,
    update_company_router,
)
from src.modules.crm.presentation.http.contact.controller import (
    create_contact_router,
    delete_contact_router,
    describe_contact_fields_router,
    get_contact_router,
    list_contacts_router,
    update_contact_router,
)

router = APIRouter()
router.include_router(create_contact_router)
router.include_router(list_contacts_router)
router.include_router(describe_contact_fields_router)
router.include_router(get_contact_router)
router.include_router(update_contact_router)
router.include_router(delete_contact_router)
router.include_router(create_company_router)
router.include_router(list_companies_router)
router.include_router(describe_company_fields_router)
router.include_router(get_company_router)
router.include_router(update_company_router)
router.include_router(delete_company_router)

__all__ = ["router"]
