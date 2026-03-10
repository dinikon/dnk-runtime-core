from dataclasses import dataclass
from typing import Self
from uuid import UUID

import uuid6


@dataclass(frozen=True, slots=True)
class ContactPointId:
    value: UUID

    @classmethod
    def new(cls) -> Self:
        return cls(value=uuid6.uuid7())

    @classmethod
    def from_value(cls, value: UUID | str) -> Self:
        if isinstance(value, str):
            value = UUID(value)
        return cls(value=value)

    def __str__(self) -> str:
        return str(self.value)


@dataclass(frozen=True, slots=True)
class ContactPointKind:
    value: str

    ALLOWED = {"phone", "email", "website", "messenger"}

    def __post_init__(self) -> None:
        normalized = self.value.strip().lower()
        if normalized not in self.ALLOWED:
            raise ValueError(f"Unsupported contact point kind: {self.value}")
        object.__setattr__(self, "value", normalized)

    @classmethod
    def phone(cls) -> "ContactPointKind":
        return cls("phone")

    @classmethod
    def email(cls) -> "ContactPointKind":
        return cls("email")

    @classmethod
    def website(cls) -> "ContactPointKind":
        return cls("website")

    @classmethod
    def messenger(cls) -> "ContactPointKind":
        return cls("messenger")


@dataclass(frozen=True, slots=True)
class ContactPointTypeCode:
    """
    Расширяемый код типа из словаря.
    Примеры:
    - work
    - mobile
    - fax
    - personal
    - telegram
    - instagram
    - primary
    """

    value: str

    def __post_init__(self) -> None:
        normalized = self.value.strip().lower()
        if not normalized:
            raise ValueError("ContactPointTypeCode cannot be empty")
        object.__setattr__(self, "value", normalized)


@dataclass(slots=True, frozen=True)
class ContactPointType:
    """
    Элемент словаря типов контактных точек.

    Примеры:
    - kind=phone, code=mobile, title="Мобильный"
    - kind=email, code=work, title="Рабочий"
    - kind=messenger, code=telegram, title="Telegram"
    """

    kind: ContactPointKind
    code: ContactPointTypeCode
    title: str
    is_system: bool = False
    is_active: bool = True
    sort_order: int = 0

    def __post_init__(self) -> None:
        title = self.title.strip()
        if not title:
            raise ValueError("ContactPointType title cannot be empty")
        object.__setattr__(self, "title", title)
