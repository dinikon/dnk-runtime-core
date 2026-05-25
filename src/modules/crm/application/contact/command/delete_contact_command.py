from dataclasses import dataclass
from uuid import UUID

from src.modules.crm.domain.contact.value_object import ContactIdVO
from src.modules.shared import EntityIdVO


@dataclass(slots=True, frozen=True)
class DeleteContactCommand:
    """Команда application-слоя на удаление контакта tenant."""

    tenant_id: EntityIdVO
    contact_id: ContactIdVO
    actor_id: UUID | None = None
