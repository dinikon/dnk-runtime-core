from __future__ import annotations

from dataclasses import dataclass
from typing import Self
from uuid import UUID

from src.modules.shared.domain import EntityIdTypeError


@dataclass(frozen=True, slots=True)
class EntityIdVO:
    """Базовый value object UUID-идентификатора доменной сущности."""

    value: UUID

    def __post_init__(self) -> None:
        """Проверяет, что value является UUID."""
        if not isinstance(self.value, UUID):
            raise EntityIdTypeError("EntityIdVO value must be UUID")

    @classmethod
    def from_value(cls, value: UUID | str | EntityIdVO | Self) -> Self:
        """Создает id из UUID, UUID-строки или другого EntityIdVO."""
        if type(value) is cls:
            return value
        if isinstance(value, EntityIdVO):
            if type(value) is not EntityIdVO:
                raise EntityIdTypeError(
                    f"{cls.__name__} cannot be created from "
                    f"{value.__class__.__name__}"
                )
            value = value.uuid
        if isinstance(value, str):
            value = UUID(value)
        return cls(value=value)

    def __str__(self) -> str:
        """Возвращает строковое представление UUID."""
        return str(self.value)

    @property
    def uuid(self) -> UUID:
        """Возвращает UUID-значение идентификатора."""
        return self.value
