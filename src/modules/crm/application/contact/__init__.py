from modules.crm.application.contact.dto import ContactDTO
from src.modules.crm.application.contact.commands import (
    AddContactCommandDTO,
    DeleteContactCommandDTO,
    UpdateContactCommandDTO,
)

from src.modules.crm.application.contact.ports import (
    ContactRecord,
    ContactRecordRepositoryPort,
    GetContactRecordQuery,
)
from src.modules.crm.application.contact.queries import (
    GetContactQueryDTO,
    ListContactsQueryDTO,
)

__all__ = [
    "ContactDTO",
    "AddContactCommandDTO",
    "DeleteContactCommandDTO",
    "ContactRecord",
    "ContactRecordRepositoryPort",
    "GetContactQueryDTO",
    "GetContactRecordQuery",
    "ListContactsQueryDTO",
    "UpdateContactCommandDTO",
]
