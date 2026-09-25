from dataclasses import dataclass
from enum import StrEnum
from src.modules.contact_points.domain.contact_point.error import (
    InvalidContactPointError,
)


class ContactPointType(StrEnum):
    """Поддерживаемый вид контактного адреса."""

    PHONE = "phone"
    EMAIL = "email"


@dataclass(slots=True, frozen=True)
class ContactPointValueVO:
    """Каноническое значение, полученное нормализатором."""

    value: str

    def __post_init__(self):
        if (
            not isinstance(self.value, str)
            or not self.value
            or len(self.value) > 320
            or self.value != self.value.strip()
        ):
            raise InvalidContactPointError("Некорректное контактное значение.")


@dataclass(slots=True, frozen=True)
class NormalizationContext:
    """Явно выбранная страна телефонного номера."""

    country_code: str | None = None


@dataclass(slots=True, frozen=True)
class NormalizedContactPoint:
    """Каноническое значение и страна без зависимости от библиотеки."""

    value: ContactPointValueVO
    country_code: str | None = None


__all__ = [
    "ContactPointType",
    "ContactPointValueVO",
    "NormalizationContext",
    "NormalizedContactPoint",
]
