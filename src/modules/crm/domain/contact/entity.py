from dataclasses import dataclass
from datetime import datetime

from src.modules.crm.domain.contact.value_object import ContactIdVO, ContactNameVO


@dataclass(slots=True)
class ContactEntity:
    id: ContactIdVO
    created_at: datetime
    updated_at: datetime
    contact_name: ContactNameVO

    @classmethod
    def create(
        cls,
        id_: ContactIdVO,
        now: datetime,
        last_name: str,
        first_name: str | None = None,
        middle_name: str | None = None,
    ):
        return cls(
            id=id_,
            created_at=now,
            updated_at=now,
            contact_name=ContactNameVO(
                last_name=last_name,
                first_name=first_name,
                middle_name=middle_name,
            ),
        )

    def rename(
        self,
        *,
        now: datetime,
        last_name: str,
        first_name: str | None = None,
        middle_name: str | None = None,
    ) -> None:
        new_contact_name = ContactNameVO(
            last_name=last_name,
            first_name=first_name,
            middle_name=middle_name,
        )

        if self.contact_name == new_contact_name:
            return

        self.contact_name = new_contact_name
        self.updated_at = now

    def touch(self, *, now: datetime) -> None:
        self.updated_at = now
