from dataclasses import dataclass, field
from datetime import datetime
from typing import Self

from src.modules.crm.domain.contact.value_object import ContactIdVO, ContactNameVO


@dataclass(slots=True)
class ContactEntity:
    """Доменная сущность CRM-контакта."""

    id: ContactIdVO
    created_at: datetime
    updated_at: datetime
    contact_name: ContactNameVO
    status: str | None = None
    tags: list[str] = field(default_factory=list)

    @classmethod
    def create(
        cls,
        id_: ContactIdVO,
        now: datetime,
        first_name: str,
        last_name: str | None = None,
        middle_name: str | None = None,
        status: str | None = None,
        tags: tuple[str, ...] = (),
    ) -> Self:
        """Создает контакт с едиными created_at/updated_at и валидированным именем."""
        return cls(
            id=id_,
            created_at=now,
            updated_at=now,
            contact_name=ContactNameVO(
                last_name=last_name,
                first_name=first_name,
                middle_name=middle_name,
            ),
            status=status,
            tags=list(tags),
        )

    def rename(
        self,
        *,
        now: datetime,
        first_name: str,
        last_name: str | None = None,
        middle_name: str | None = None,
        status: str | None = None,
        tags: tuple[str, ...] | None = None,
    ) -> None:
        """Обновляет имя, статус и теги контакта, если данные изменились."""
        new_contact_name = ContactNameVO(
            last_name=last_name,
            first_name=first_name,
            middle_name=middle_name,
        )
        new_status = self.status if status is None else status
        new_tags = self.tags if tags is None else list(tags)

        if (
            self.contact_name == new_contact_name
            and self.status == new_status
            and self.tags == new_tags
        ):
            return

        self.contact_name = new_contact_name
        self.status = new_status
        self.tags = new_tags
        self.updated_at = now

    def touch(self, *, now: datetime) -> None:
        """Обновляет timestamp контакта без изменения бизнес-полей."""
        self.updated_at = now
