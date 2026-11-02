from dataclasses import dataclass
from typing import Self

from src.modules.inventory.domain.error import InvalidInventoryItemValueError
from src.modules.inventory.domain.value_object.conversion_factor import (
    ConversionFactorVO,
)
from src.modules.inventory.domain.value_object.item_uom_conversion_id import (
    ItemUomConversionIdVO,
)
from src.modules.inventory.domain.value_object.uom_code import UomCodeVO


@dataclass(frozen=True, slots=True)
class ItemUomConversion:
    """Прямое преобразование дополнительной единицы позиции в базовую."""

    id: ItemUomConversionIdVO
    uom: UomCodeVO
    factor: ConversionFactorVO

    @classmethod
    def create(
        cls,
        *,
        identifier: ItemUomConversionIdVO,
        uom: UomCodeVO,
        factor: ConversionFactorVO,
    ) -> Self:
        """Создаёт конвертацию с положительным коэффициентом в базовую единицу."""
        return cls.restore(identifier=identifier, uom=uom, factor=factor)

    @classmethod
    def restore(
        cls,
        *,
        identifier: ItemUomConversionIdVO,
        uom: UomCodeVO,
        factor: ConversionFactorVO,
    ) -> Self:
        """Восстанавливает конвертацию и проверяет собственные значения Entity."""
        entity = cls(id=identifier, uom=uom, factor=factor)
        entity.ensure_valid()
        return entity

    def ensure_valid(self) -> None:
        """Проверяет идентичность, код единицы и тип коэффициента."""
        if (
            not isinstance(self.id, ItemUomConversionIdVO)
            or not isinstance(self.uom, UomCodeVO)
            or not isinstance(self.factor, ConversionFactorVO)
        ):
            raise InvalidInventoryItemValueError("Некорректное состояние конвертации.")
