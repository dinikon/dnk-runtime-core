from dataclasses import dataclass
from typing import Self

from src.modules.inventory.domain.inventory_item.error import (
    InvalidInventoryItemValueError,
)
from src.modules.inventory.domain.inventory_item.value_object.item_packaging_id import (
    ItemPackagingIdVO,
)
from src.modules.inventory.domain.inventory_item.value_object.packaging_quantity import (
    PackagingQuantityVO,
)
from src.modules.inventory.domain.packaging_type.value_object.identifier import (
    PackagingTypeIdVO,
)
from src.modules.inventory.domain.value_object.packaging_code import PackagingCodeVO
from src.modules.inventory.domain.value_object.packaging_name import PackagingNameVO
from src.modules.inventory.domain.value_object.uom_code import UomCodeVO


@dataclass(frozen=True, slots=True)
class ItemPackaging:
    """Способ упаковки товара с явным количеством и единицей содержимого."""

    id: ItemPackagingIdVO
    packaging_type_id: PackagingTypeIdVO
    code: PackagingCodeVO
    name: PackagingNameVO
    content_quantity: PackagingQuantityVO
    content_uom: UomCodeVO

    @classmethod
    def create(
        cls,
        *,
        identifier: ItemPackagingIdVO,
        packaging_type_id: PackagingTypeIdVO,
        code: PackagingCodeVO,
        name: PackagingNameVO,
        content_quantity: PackagingQuantityVO,
        content_uom: UomCodeVO,
    ) -> Self:
        """Создаёт вариант; размерность содержимого проверяет InventoryItem."""
        return cls.restore(
            identifier=identifier,
            packaging_type_id=packaging_type_id,
            code=code,
            name=name,
            content_quantity=content_quantity,
            content_uom=content_uom,
        )

    @classmethod
    def restore(
        cls,
        *,
        identifier: ItemPackagingIdVO,
        packaging_type_id: PackagingTypeIdVO,
        code: PackagingCodeVO,
        name: PackagingNameVO,
        content_quantity: PackagingQuantityVO,
        content_uom: UomCodeVO,
    ) -> Self:
        """Восстанавливает идентичность варианта и его собственные значения."""
        value = cls(
            identifier, packaging_type_id, code, name, content_quantity, content_uom
        )
        value.ensure_valid()
        return value

    def ensure_valid(self) -> None:
        """Проверяет собственные типы Entity без правил родительского агрегата."""
        if (
            not isinstance(self.id, ItemPackagingIdVO)
            or not isinstance(self.packaging_type_id, PackagingTypeIdVO)
            or not isinstance(self.code, PackagingCodeVO)
            or not isinstance(self.name, PackagingNameVO)
            or not isinstance(self.content_quantity, PackagingQuantityVO)
            or not isinstance(self.content_uom, UomCodeVO)
        ):
            raise InvalidInventoryItemValueError(
                "Некорректное состояние упаковки товара."
            )
