from dataclasses import dataclass
from typing import Self

from src.modules.inventory.domain.inventory_item.error import (
    InvalidInventoryItemValueError,
)
from src.modules.inventory.domain.inventory_item.value_object.barcode import BarcodeVO
from src.modules.inventory.domain.inventory_item.value_object.item_barcode_id import (
    ItemBarcodeIdVO,
)


@dataclass(frozen=True, slots=True)
class ItemBarcode:
    """Штрихкод, идентифицирующий только родительский InventoryItem."""

    id: ItemBarcodeIdVO
    barcode: BarcodeVO

    @classmethod
    def create(
        cls,
        *,
        identifier: ItemBarcodeIdVO,
        barcode: BarcodeVO,
    ) -> Self:
        """Создаёт идентификатор товара без привязки к упаковке или количеству."""
        return cls.restore(identifier=identifier, barcode=barcode)

    @classmethod
    def restore(
        cls,
        *,
        identifier: ItemBarcodeIdVO,
        barcode: BarcodeVO,
    ) -> Self:
        """Восстанавливает штрихкод, проверяя собственные типы без правил агрегата."""
        entity = cls(id=identifier, barcode=barcode)
        entity.ensure_valid()
        return entity

    def ensure_valid(self) -> None:
        """Проверяет идентичность и собственные значения Entity."""
        if not isinstance(self.id, ItemBarcodeIdVO) or not isinstance(
            self.barcode, BarcodeVO
        ):
            raise InvalidInventoryItemValueError("Некорректное состояние штрихкода.")
