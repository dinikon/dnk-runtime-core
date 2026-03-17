from dataclasses import dataclass

from src.modules.crm.domain.contact.value_object.contact_id import ContactIdVO


@dataclass(slots=True, frozen=True)
class RenameContactCommand:
    contact_id: ContactIdVO
    last_name: str
    first_name: str | None = None
    middle_name: str | None = None
