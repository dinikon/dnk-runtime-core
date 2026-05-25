from dataclasses import dataclass
from uuid import UUID

from src.modules.crm.domain.contact.value_object import ContactIdVO
from src.modules.shared import EntityIdVO


@dataclass(slots=True, frozen=True)
class CreateContactCommand:
    """Команда application-слоя на создание контакта tenant."""

    tenant_id: EntityIdVO
    contact_id: ContactIdVO
    first_name: str
    last_name: str | None = None
    middle_name: str | None = None
    status: str | None = None
    tags: tuple[str, ...] = ()
    actor_id: UUID | None = None
