from dataclasses import dataclass
from decimal import Decimal
from typing import Self
from src.modules.catalog.domain.catalog_item.value_object.override import OverrideMode


@dataclass(frozen=True, slots=True)
class CatalogMetadataEntry:
    """Типизированный собственный ключ либо явная очистка родительского ключа."""

    key: str
    value_type: str | None
    value: str | Decimal | bool | None
    position: int
    mode: OverrideMode

    @classmethod
    def create(
        cls,
        key: str,
        value_type: str | None,
        value: str | Decimal | bool | None,
        position: int,
        mode: OverrideMode,
    ) -> Self:
        """Создаёт запись; набор и допустимость ключей проверяет CatalogItem."""
        return cls(key, value_type, value, position, mode)

    @classmethod
    def restore(
        cls,
        key: str,
        value_type: str | None,
        value: str | Decimal | bool | None,
        position: int,
        mode: OverrideMode,
    ) -> Self:
        """Восстанавливает запись без подмены типа и значения."""
        return cls(key, value_type, value, position, mode)
