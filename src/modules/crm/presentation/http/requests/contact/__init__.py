from src.modules.crm.presentation.http.requests.contact.add import (
    AddContactRequestSchema,
)
from src.modules.crm.presentation.http.requests.contact.delete import (
    DeleteContactRequestSchema,
)
from src.modules.crm.presentation.http.requests.contact.get import (
    GetContactRequestSchema,
)
from src.modules.crm.presentation.http.requests.contact.list import (
    ListContactsRequestSchema,
)
from src.modules.crm.presentation.http.requests.contact.update import (
    UpdateContactRequestSchema,
)

__all__ = [
    "AddContactRequestSchema",
    "DeleteContactRequestSchema",
    "GetContactRequestSchema",
    "ListContactsRequestSchema",
    "UpdateContactRequestSchema",
]
