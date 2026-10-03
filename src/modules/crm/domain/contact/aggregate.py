from dataclasses import dataclass
from datetime import datetime
from typing import Self

from src.modules.crm.domain.contact.error import InvalidContactNameError
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

    def replace_name(
        self,
        *,
        first_name: str | None,
        last_name: str | None,
        middle_name: str | None,
        actor_id: EntityIdVO,
        now: datetime,
    ) -> bool:
        """Проверяет новое ФИО и обновляет аудит только при изменении."""
        if not isinstance(first_name, str) or not isinstance(last_name, str):
            raise InvalidContactNameError(
                "first_name и last_name должны быть строками."
            )
        name = ContactNameVO(first_name, last_name, middle_name)
        if name == self.name:
            return False
        self.name = name
        self.updated_at = now
        self.updated_by = actor_id
        return True
