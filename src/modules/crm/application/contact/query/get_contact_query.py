from dataclasses import dataclass

from src.modules.crm.domain.contact.value_object.contact_id import ContactIdVO


@dataclass(slots=True, frozen=True)
class GetContactQuery:
    contact_id: ContactIdVO
