from dataclasses import dataclass, replace
from typing import Self
from uuid import UUID

import uuid6

from src.modules.crm.domain.error import (
    ContactPointKindNotSupportedError,
    ContactPointTypeCodeRequiredError,
    ContactPointTypeTitleRequiredError,
)


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

    ALLOWED = {"phone", "email", "site", "messenger"}
    ALIASES = {"website": "site"}

    def __post_init__(self) -> None:
        normalized = self.value.strip().lower()
        normalized = self.ALIASES.get(normalized, normalized)
        if normalized not in self.ALLOWED:
            raise ContactPointKindNotSupportedError(self.value)
        object.__setattr__(self, "value", normalized)

    @classmethod
    def phone(cls) -> "ContactPointKind":
        return cls("phone")

    @classmethod
    def email(cls) -> "ContactPointKind":
        return cls("email")

    @classmethod
    def site(cls) -> "ContactPointKind":
        return cls("site")

    @classmethod
    def website(cls) -> "ContactPointKind":
        # Backward compatibility alias.
        return cls("site")

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
            raise ContactPointTypeCodeRequiredError()
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
            raise ContactPointTypeTitleRequiredError()
        object.__setattr__(self, "title", title)

    def rename(self, title: str) -> "ContactPointType":
        normalized_title = title.strip()
        if not normalized_title:
            raise ContactPointTypeTitleRequiredError()
        return replace(self, title=normalized_title)

    def activate(self) -> "ContactPointType":
        return replace(self, is_active=True)

    def deactivate(self) -> "ContactPointType":
        return replace(self, is_active=False)

    def reorder(self, sort_order: int) -> "ContactPointType":
        return replace(self, sort_order=sort_order)
