from dataclasses import dataclass

from src.modules.crm.domain.contact.value_object.identifier import ContactIdVO
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


@dataclass(frozen=True, slots=True)
class UpdateContactCommand:
    """Полное либо частичное изменение ФИО контакта."""

    contact_id: ContactIdVO
    actor_id: EntityIdVO
    fields: frozenset[str]
    first_name: str | None = None
    last_name: str | None = None
    middle_name: str | None = None
