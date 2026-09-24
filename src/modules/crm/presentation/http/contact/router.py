from fastapi import APIRouter

from src.modules.crm.presentation.http.contact.controller import (
    create_contact_router,
    delete_contact_router,
    get_contact_router,
    list_contacts_router,
    update_contact_router,
)

router = APIRouter()
for action_router in (
    create_contact_router,
    list_contacts_router,
    get_contact_router,
    update_contact_router,
    delete_contact_router,
):
    router.include_router(action_router, prefix="/contacts", tags=["crm-contacts"])

__all__ = ["router"]
