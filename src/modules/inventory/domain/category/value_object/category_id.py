from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from src.modules.shared import EntityIdVO


@dataclass(frozen=True, slots=True)
class CategoryIdVO:
    """Value object идентификатора категории товаров."""

    value: EntityIdVO

    @classmethod
    def from_value(cls, value: UUID | str | EntityIdVO) -> "CategoryIdVO":
        """Создает CategoryIdVO из UUID, строки или готового EntityIdVO."""
        if isinstance(value, EntityIdVO):
            return cls(value=value)
        return cls(value=EntityIdVO.from_value(value))

    def __str__(self) -> str:
        """Возвращает строковое представление id категории."""
        return str(self.value)

    @property
    def uuid(self) -> UUID:
        """Возвращает UUID-значение id категории."""
        return self.value.value
