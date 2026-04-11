from dataclasses import dataclass


from src.modules.crm.domain.contact.value_object import ContactIdVO
from src.modules.shared import EntityIdVO


@dataclass(slots=True, frozen=True)
class CreateContactCommand:
    tenant_id: EntityIdVO
    contact_id: ContactIdVO
    last_name: str
    first_name: str | None = None
    middle_name: str | None = None
