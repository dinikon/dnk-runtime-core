from dataclasses import dataclass, field
from datetime import datetime
from typing import Self

from src.modules.crm.domain.contact.value_objects import ContactIdVO, PersonNameVO


@dataclass(slots=True)
class ContactEntity:
    id: ContactIdVO
    created_at: datetime
    updated_at: datetime

    name: PersonNameVO

    @classmethod
    def create(
        cls,
        created_at: datetime,
        updated_at: datetime,
        first_name: str,
        last_name: str | None = None,
        middle_name: str | None = None,
    ) -> Self:
        return cls(
            id=ContactIdVO.new(),
            created_at=created_at,
            updated_at=updated_at,
            name=PersonNameVO(
                first_name=first_name,
                last_name=last_name,
                middle_name=middle_name,
            ),
        )

    @property
    def first_name(self) -> str:
        return self.name.first_name

    @property
    def last_name(self) -> str | None:
        return self.name.last_name

    @property
    def middle_name(self) -> str | None:
        return self.name.middle_name

    def rename(
        self,
        first_name: str,
        last_name: str | None = None,
        middle_name: str | None = None,
    ) -> None:
        self.name = PersonNameVO(
            first_name=first_name,
            last_name=last_name,
            middle_name=middle_name,
        )
