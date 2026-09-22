from dataclasses import dataclass

from src.modules.crm.domain.contact.value_object import ContactIdVO
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


@dataclass(slots=True, frozen=True)
class DeleteContactCommand:
    """Параметры физического удаления контакта."""

    tenant_id: EntityIdVO
    contact_id: ContactIdVO


__all__ = ["DeleteContactCommand"]
