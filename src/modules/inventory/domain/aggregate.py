from dataclasses import dataclass
from typing import Self

from src.modules.inventory.domain.value_object.identifier import InventoryItemIdVO


@dataclass(frozen=True, slots=True)
class InventoryItem:
    """Корень агрегата складской номенклатуры."""

    id: InventoryItemIdVO

    @classmethod
    def create(cls, *, identifier: InventoryItemIdVO) -> Self:
        """Создаёт складскую позицию с переданным идентификатором."""
        return cls(id=InventoryItemIdVO.from_value(identifier))

    @classmethod
    def restore(cls, *, identifier: InventoryItemIdVO) -> Self:
        """Восстанавливает складскую позицию с сохранённым идентификатором."""
        return cls(id=InventoryItemIdVO.from_value(identifier))
