from src.modules.crm.application.contact.query.get_contact_query import GetContactQuery
from src.modules.crm.application.contact.query.list_contacts_query import (
    ListContactsQuery,
)
from src.modules.crm.application.contact.query.describe_contact_fields_repository import (
    ContactFieldsDescriptionRepositoryProtocol,
)
from src.modules.crm.application.contact.query.repository import (
    ContactQueryRepositoryProtocol,
)

__all__ = [
    "ContactFieldsDescriptionRepositoryProtocol",
    "ContactQueryRepositoryProtocol",
    "GetContactQuery",
    "ListContactsQuery",
]
