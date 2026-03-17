from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from src.modules.crm.domain.contact.value_object.contact_name import ContactNameVO
from src.modules.crm.domain.contact.value_object.contact_id import ContactIdVO


@dataclass(slots=True)
class ContactEntity:
    id: ContactIdVO
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime
    contact_name: ContactNameVO

    @classmethod
    def create(
        cls,
        id_: ContactIdVO,
        tenant_id: UUID,
        now: datetime,
        last_name: str,
        first_name: str | None = None,
        middle_name: str | None = None,
    ):
        return cls(
            id=id_,
            tenant_id=tenant_id,
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
