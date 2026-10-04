from dataclasses import dataclass

from src.modules.crm.domain.contact.value_object.identifier import ContactIdVO


@dataclass(frozen=True, slots=True)
class ListContactCompaniesQuery:
    contact_id: ContactIdVO
