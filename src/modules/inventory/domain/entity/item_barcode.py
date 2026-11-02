from dataclasses import dataclass
from typing import Self

from src.modules.inventory.domain.error import InvalidInventoryItemValueError
from src.modules.inventory.domain.value_object.barcode import BarcodeVO
from src.modules.inventory.domain.value_object.item_barcode_id import ItemBarcodeIdVO
from src.modules.inventory.domain.value_object.uom_code import UomCodeVO


@dataclass(frozen=True, slots=True)
class ItemBarcode:
    """Штрихкод единицы или упаковки, принадлежащий складской позиции."""

    id: ItemBarcodeIdVO
    barcode: BarcodeVO
    uom: UomCodeVO

    @classmethod
    def create(
        cls, *, identifier: ItemBarcodeIdVO, barcode: BarcodeVO, uom: UomCodeVO
    ) -> Self:
        """Создаёт штрихкод с явно переданным идентификатором и единицей."""
        return cls.restore(identifier=identifier, barcode=barcode, uom=uom)

    @classmethod
    def restore(
        cls, *, identifier: ItemBarcodeIdVO, barcode: BarcodeVO, uom: UomCodeVO
    ) -> Self:
        """Восстанавливает штрихкод, проверяя собственные типы без правил агрегата."""
        entity = cls(id=identifier, barcode=barcode, uom=uom)
        entity.ensure_valid()
        return entity

    def ensure_valid(self) -> None:
        """Проверяет идентичность и собственные значения Entity."""
        if (
            not isinstance(self.id, ItemBarcodeIdVO)
            or not isinstance(self.barcode, BarcodeVO)
            or not isinstance(self.uom, UomCodeVO)
        ):
            raise InvalidInventoryItemValueError("Некорректное состояние штрихкода.")
