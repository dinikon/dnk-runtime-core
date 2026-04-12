from dataclasses import dataclass

from src.modules.crm.domain.contact.value_object import ContactIdVO
from src.modules.shared import EntityIdVO


@dataclass(slots=True, frozen=True)
class GetContactQuery:
    """Query application-слоя на получение одного контакта tenant."""

    tenant_id: EntityIdVO
    contact_id: ContactIdVO
