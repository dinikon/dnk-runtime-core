from dataclasses import dataclass
from datetime import datetime

from src.modules.crm.domain.contact.value_object import ContactIdVO, ContactNameVO
from src.modules.shared.domain.domain_error import EntityIdTypeError
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


@dataclass(slots=True)
class Contact:
    """Физическое лицо в CRM."""

    id: ContactIdVO
    name: ContactNameVO
    created_at: datetime
    updated_at: datetime
    created_by: EntityIdVO
    updated_by: EntityIdVO

    def __post_init__(self) -> None:
        if type(self.id) is not ContactIdVO:
            raise EntityIdTypeError("Contact id must use ContactIdVO.")
        if not isinstance(self.created_by, EntityIdVO) or not isinstance(
            self.updated_by, EntityIdVO
        ):
            raise EntityIdTypeError("Contact audit ids must use EntityIdVO.")
        if not isinstance(self.name, ContactNameVO):
            raise TypeError("Contact name must use ContactNameVO.")

    @classmethod
    def create(
        cls,
        *,
        contact_id: ContactIdVO,
        actor_id: EntityIdVO,
        now: datetime,
        first_name: str,
        last_name: str | None = None,
        middle_name: str | None = None,
    ) -> "Contact":
        """Создаёт контакт с едиными audit-значениями."""
        return cls(
            id=contact_id,
            name=ContactNameVO(
                first_name=first_name,
                last_name=last_name,
                middle_name=middle_name,
            ),
            created_at=now,
            updated_at=now,
            created_by=actor_id,
            updated_by=actor_id,
        )

    def update(
        self,
        *,
        actor_id: EntityIdVO,
        now: datetime,
        first_name: str,
        last_name: str | None = None,
        middle_name: str | None = None,
    ) -> bool:
        """Меняет ФИО и audit только при фактическом изменении."""
        name = ContactNameVO(
            first_name=first_name,
            last_name=last_name,
            middle_name=middle_name,
        )
        if name == self.name:
            return False
        self.name = name
        self.updated_at = now
        self.updated_by = actor_id
        return True


__all__ = ["Contact"]
