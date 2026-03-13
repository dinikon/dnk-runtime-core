from dataclasses import dataclass

from modules.crm.application.contact.queries.contact_list_filter import (
    ContactListFilter,
)
from modules.crm.application.contact.queries.contact_sort import ContactSort


@dataclass(frozen=True, slots=True)
class ListContactsQueryDTO:
    filter: ContactListFilter
    sort: ContactSort = ContactSort()
    limit: int = 50
    offset: int = 0
