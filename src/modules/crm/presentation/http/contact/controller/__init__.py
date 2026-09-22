from src.modules.crm.presentation.http.contact.controller.create_contact import (
    router as create_contact_router,
)
from src.modules.crm.presentation.http.contact.controller.delete_contact import (
    router as delete_contact_router,
)
from src.modules.crm.presentation.http.contact.controller.get_contact import (
    router as get_contact_router,
)
from src.modules.crm.presentation.http.contact.controller.list_contacts import (
    router as list_contacts_router,
)
from src.modules.crm.presentation.http.contact.controller.update_contact import (
    router as update_contact_router,
)

__all__ = [
    "create_contact_router",
    "delete_contact_router",
    "get_contact_router",
    "list_contacts_router",
    "update_contact_router",
]
