from dataclasses import dataclass

from src.modules.crm.domain.contact.value_object.identifier import ContactIdVO
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


@dataclass(frozen=True, slots=True)
class DeleteContactCommand:
    """Удаление контакта по идентификатору в текущем tenant."""

    contact_id: ContactIdVO
    tenant_id: EntityIdVO
