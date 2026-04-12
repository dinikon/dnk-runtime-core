from dataclasses import dataclass
from typing import Self
from uuid import UUID

import uuid6

from src.modules.shared.domain.errors import EntityIdTypeError


@dataclass(frozen=True, slots=True)
class EntityIdVO:
    """Value object UUID-идентификатора доменной сущности."""

    value: UUID

    def __post_init__(self) -> None:
        """Проверяет, что value является UUID."""
        if not isinstance(self.value, UUID):
            raise EntityIdTypeError("EntityIdVO value must be UUID")

    @classmethod
    def from_value(cls, value: UUID | str) -> Self:
        """Создает EntityIdVO из UUID или UUID-строки."""
        if isinstance(value, str):
            value = UUID(value)
        return cls(value=value)

    def __str__(self) -> str:
        """Возвращает строковое представление UUID."""
        return str(self.value)
