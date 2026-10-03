from dataclasses import dataclass
from datetime import datetime
from typing import Self

from src.modules.crm.domain.contact.value_object.identifier import ContactIdVO
from src.modules.crm.domain.contact.value_object.name import ContactNameVO
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


@dataclass(slots=True)
class ContactEntity:
    """Самостоятельный контакт с полным именем и аудитом изменений."""

    id: ContactIdVO
    name: ContactNameVO
    created_at: datetime
    updated_at: datetime
    created_by: EntityIdVO
    updated_by: EntityIdVO

    @classmethod
    def create(
        cls,
        *,
        contact_id: ContactIdVO,
        first_name: str,
        last_name: str,
        actor_id: EntityIdVO,
        now: datetime,
        middle_name: str | None = None,
    ) -> Self:
        """Создаёт контакт с проверенным именем и первоначальным аудитом."""
        return cls(
            id=contact_id,
            name=ContactNameVO(first_name, last_name, middle_name),
            created_at=now,
            updated_at=now,
            created_by=actor_id,
            updated_by=actor_id,
        )
