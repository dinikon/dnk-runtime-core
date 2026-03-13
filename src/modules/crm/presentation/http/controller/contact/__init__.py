from src.modules.crm.presentation.http.controller.contact.add import (
    router as add_contact_router,
)
from src.modules.crm.presentation.http.controller.contact.delete import (
    router as delete_contact_router,
)
from src.modules.crm.presentation.http.controller.contact.get import (
    router as get_contact_router,
)
from src.modules.crm.presentation.http.controller.contact.list import (
    router as list_contacts_router,
)
from src.modules.crm.presentation.http.controller.contact.update import (
    router as update_contact_router,
)

__all__ = [
    "add_contact_router",
    "delete_contact_router",
    "get_contact_router",
    "list_contacts_router",
    "update_contact_router",
]
