from dataclasses import dataclass

from src.modules.crm.domain.contact.value_object.identifier import ContactIdVO
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


@dataclass(frozen=True, slots=True)
class CreateContactCommand:
    """Намерение создать контакт от имени участника tenant."""

    actor_id: EntityIdVO
    contact_id: ContactIdVO
    first_name: str
    last_name: str
    middle_name: str | None = None
