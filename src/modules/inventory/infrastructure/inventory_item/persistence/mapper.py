from collections.abc import Mapping, Sequence
from typing import Any

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


class InventoryItemMapper:
    """Извлекает представление записи агрегата без SQL и бизнес-проверок."""

    @staticmethod
    def to_domain(
        row: Mapping[str, Any], barcode_rows: Sequence[Mapping[str, Any]]
    ) -> InventoryItem:
        """Восстанавливает полный сохранённый состав с исходными идентификаторами."""
        return InventoryItem.restore(
            identifier=InventoryItemIdVO.from_value(row["id"]),
            sku=SkuVO(row["sku"]),
            base_uom=UomCodeVO(row["base_uom"]),
            quantity_rules=QuantityRulesVO(row["quantity_step"]),
            tracking_mode=TrackingMode(row["tracking_mode"]),
            expiration_mode=ExpirationMode(row["expiration_mode"]),
            packagings=(),
            barcodes=tuple(
                ItemBarcode.restore(
                    identifier=ItemBarcodeIdVO.from_value(child["id"]),
                    barcode=BarcodeVO(child["barcode"]),
                )
                for child in barcode_rows
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
