from dataclasses import dataclass

from src.modules.crm.domain.contact.value_object.identifier import ContactIdVO
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


@dataclass(frozen=True, slots=True)
class GetContactQuery:
    """Параметры чтения одного контакта в доверенном tenant-контексте."""

    tenant_id: EntityIdVO
    contact_id: ContactIdVO
