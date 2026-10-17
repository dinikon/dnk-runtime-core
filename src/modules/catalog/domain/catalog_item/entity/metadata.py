from dataclasses import dataclass
from decimal import Decimal
from typing import Self


@dataclass(frozen=True, slots=True)
class CatalogMetadataEntry:
    """Типизированное дополнительное значение самостоятельного товара."""

    key: str
    value_type: str
    value: str | Decimal | bool
    position: int

    @classmethod
    def create(
        cls,
        key: str,
        value_type: str,
        value: str | Decimal | bool,
        position: int,
    ) -> Self:
        """Создаёт запись; набор и допустимость ключей проверяет CatalogItem."""
        return cls(key, value_type, value, position)

    @classmethod
    def restore(
        cls,
        key: str,
        value_type: str,
        value: str | Decimal | bool,
        position: int,
    ) -> Self:
        """Восстанавливает запись без подмены типа и значения."""
        return cls(key, value_type, value, position)
