from dataclasses import dataclass
from datetime import datetime

from src.modules.crm.domain.contact.entity import Contact
from src.modules.crm.domain.contact.value_object import ContactIdVO
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


@dataclass(slots=True, frozen=True)
class ContactDTO:
    """Публичные данные CRM-контакта."""

    id: ContactIdVO
    first_name: str
    last_name: str | None
    middle_name: str | None
    created_at: datetime
    updated_at: datetime
    created_by: EntityIdVO
    updated_by: EntityIdVO


@dataclass(slots=True, frozen=True)
class ContactPageDTO:
    """Страница контактов с полным количеством результатов."""

    items: tuple[ContactDTO, ...]
    total: int
    limit: int
    offset: int


def contact_dto(contact: Contact) -> ContactDTO:
    """Преобразует aggregate контакта в application DTO."""
    return ContactDTO(
        id=contact.id,
        first_name=contact.name.first_name,
        last_name=contact.name.last_name,
        middle_name=contact.name.middle_name,
        created_at=contact.created_at,
        updated_at=contact.updated_at,
        created_by=contact.created_by,
        updated_by=contact.updated_by,
    )


__all__ = ["ContactDTO", "ContactPageDTO", "contact_dto"]
