from dataclasses import dataclass

from src.modules.crm.domain.contact.value_object.identifier import ContactIdVO


@dataclass(frozen=True, slots=True)
class DeleteContactCommand:
    """Удаление контакта по идентификатору в текущем tenant."""

    contact_id: ContactIdVO
