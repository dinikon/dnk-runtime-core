from collections.abc import Sequence
from typing import Any

from src.modules.inventory.domain.inventory_item.entity.item_packaging import (
    ItemPackaging,
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
from src.modules.inventory.infrastructure.persistence.models.item_packaging import (
    ItemPackagingModel,
)
from src.modules.inventory.domain.inventory_item.aggregate import InventoryItem
from src.modules.inventory.domain.inventory_item.entity.item_barcode import ItemBarcode
from src.modules.inventory.domain.inventory_item.value_object.barcode import BarcodeVO
from src.modules.inventory.domain.inventory_item.value_object.identifier import (
    InventoryItemIdVO,
)
from src.modules.inventory.domain.inventory_item.value_object.item_barcode_id import (
    ItemBarcodeIdVO,
)
from src.modules.inventory.domain.inventory_item.value_object.sku import SkuVO
from src.modules.inventory.domain.inventory_item.value_object.expiration_mode import (
    ExpirationMode,
)
from src.modules.inventory.domain.inventory_item.value_object.tracking_mode import (
    TrackingMode,
)
from src.modules.inventory.domain.value_object.quantity_rules import QuantityRulesVO
from src.modules.inventory.domain.value_object.uom_code import UomCodeVO
from src.modules.inventory.infrastructure.persistence.models.inventory_item import (
    InventoryItemModel,
)
from src.modules.inventory.infrastructure.persistence.models.item_barcode import (
    ItemBarcodeModel,
)


class InventoryItemMapper:
    """Преобразует ORM-модели и агрегат без SQL и бизнес-проверок."""

    @staticmethod
    def to_domain(
        model: InventoryItemModel,
        barcode_models: Sequence[ItemBarcodeModel],
        packaging_models: Sequence[ItemPackagingModel],
    ) -> InventoryItem:
        """Восстанавливает полный сохранённый состав с исходными идентификаторами."""
        return InventoryItem.restore(
            identifier=InventoryItemIdVO.from_value(model.id),
            sku=SkuVO(model.sku),
            base_uom=UomCodeVO(model.base_uom),
            quantity_rules=QuantityRulesVO(model.quantity_step),
            tracking_mode=TrackingMode(model.tracking_mode),
            expiration_mode=ExpirationMode(model.expiration_mode),
            packagings=tuple(
                ItemPackaging.restore(
                    identifier=ItemPackagingIdVO.from_value(child.id),
                    packaging_type_id=PackagingTypeIdVO.from_value(
                        child.packaging_type_id
                    ),
                    code=PackagingCodeVO(child.code),
                    name=PackagingNameVO(child.name),
                    content_quantity=PackagingQuantityVO(child.content_quantity),
                    content_uom=UomCodeVO(child.content_uom),
                )
                for child in packaging_models
            ),
            barcodes=tuple(
                ItemBarcode.restore(
                    identifier=ItemBarcodeIdVO.from_value(child.id),
                    barcode=BarcodeVO(child.barcode),
                )
                for child in barcode_models
            ),
        )

    @staticmethod
    def to_insert_values(item: InventoryItem) -> dict[str, Any]:
        """Возвращает скалярные настройки позиции, сохраняя точный Decimal."""
        return {
            "id": item.id.uuid,
            "sku": item.sku.value,
            "base_uom": item.base_uom.value,
            "quantity_step": item.quantity_rules.step,
            "tracking_mode": item.tracking_mode.value,
            "expiration_mode": item.expiration_mode.value,
        }

    @staticmethod
    def to_update_values(item: InventoryItem) -> dict[str, Any]:
        """Извлекает новое состояние существующего корня без замены его идентичности."""
        values = InventoryItemMapper.to_insert_values(item)
        del values["id"]
        return values

    @staticmethod
    def to_barcode_insert_values(item: InventoryItem) -> list[dict[str, Any]]:
        """Извлекает дочерние штрихкоды с исходными ID и порядком."""
        return [
            {
                "id": barcode.id.uuid,
                "inventory_item_id": item.id.uuid,
                "barcode": barcode.barcode.value,
                "position": position,
            }
            for position, barcode in enumerate(item.barcodes)
        ]

    @staticmethod
    def to_packaging_insert_values(item: InventoryItem) -> list[dict[str, Any]]:
        """Извлекает упаковки с доменными ID, точными Decimal и сохранённым порядком."""
        return [
            {
                "id": child.id.uuid,
                "inventory_item_id": item.id.uuid,
                "packaging_type_id": child.packaging_type_id.uuid,
                "code": child.code.value,
                "name": child.name.value,
                "content_quantity": child.content_quantity.value,
                "content_uom": child.content_uom.value,
                "position": position,
            }
            for position, child in enumerate(item.packagings)
        ]
