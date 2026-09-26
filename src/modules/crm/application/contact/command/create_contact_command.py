from dataclasses import dataclass
from src.modules.crm.application.contact_points.port import ContactPointInputDTO

from src.modules.crm.domain.contact.value_object import ContactIdVO
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


@dataclass(slots=True, frozen=True)
class CreateContactCommand:
    """Входные данные создания контакта."""

    tenant_id: EntityIdVO
    actor_id: EntityIdVO
    contact_id: ContactIdVO
    first_name: str
    last_name: str | None = None
    middle_name: str | None = None
    phones: tuple[ContactPointInputDTO, ...] | None = None
    emails: tuple[ContactPointInputDTO, ...] | None = None


__all__ = ["CreateContactCommand"]
