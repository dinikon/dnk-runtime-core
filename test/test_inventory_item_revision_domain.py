"""Атомарные изменения InventoryItem через публичные Domain-методы."""

from decimal import Decimal
import unittest
from uuid import uuid4

from src.modules.inventory.domain.error import InventoryError
from src.modules.inventory.domain.inventory_item.aggregate import InventoryItem
from src.modules.inventory.domain.inventory_item.value_object.identifier import (
    InventoryItemIdVO,
)
from src.modules.inventory.domain.inventory_item.value_object.sku import SkuVO
from src.modules.inventory.domain.inventory_item.value_object.tracking_mode import (
    TrackingMode,
)
from src.modules.inventory.domain.inventory_item.value_object.expiration_mode import (
    ExpirationMode,
)
from src.modules.inventory.domain.value_object.quantity_rules import QuantityRulesVO
from src.modules.inventory.domain.value_object.uom_code import UomCodeVO


def make_item() -> InventoryItem:
    """Создаёт минимальную позицию с известными настройками."""
    return InventoryItem.create(
        identifier=InventoryItemIdVO(uuid4()),
        sku=SkuVO("Item"),
        base_uom=UomCodeVO("PCS"),
        quantity_rules=QuantityRulesVO(Decimal("1")),
    )


def revise(item: InventoryItem, **changes: object) -> InventoryItem:
    """Передаёт итоговый полный состав публичному методу пересмотра."""
    values = dict(
        sku=item.sku,
        base_uom=item.base_uom,
        quantity_rules=item.quantity_rules,
        tracking_mode=item.tracking_mode,
        expiration_mode=item.expiration_mode,
        barcodes=item.barcodes,
    )
    return item.revise(**(values | changes))


class InventoryItemRevisionDomainTests(unittest.TestCase):
    """Проверяет итоговое состояние и неизменяемость исходной позиции при отказе."""

    def test_noop_preserves_instance(self) -> None:
        """Нормализованное равное значение не создаёт лишний экземпляр."""
        item = make_item()
        self.assertIs(item.change_sku(SkuVO(" ITEM ")), item)
        changed = item.change_sku(SkuVO("Another"))
        self.assertEqual(changed.sku.value, "another")
        self.assertEqual(item.sku.value, "item")
        self.assertIs(revise(changed), changed)

    def test_revise_validates_only_final_tracking_configuration(self) -> None:
        """Серийная позиция переходит в партионную с новой единицей и шагом атомарно."""
        serial = revise(make_item(), tracking_mode=TrackingMode.SERIAL)
        changed = revise(
            serial,
            tracking_mode=TrackingMode.LOT,
            expiration_mode=ExpirationMode.REQUIRED,
            base_uom=UomCodeVO("KG"),
            quantity_rules=QuantityRulesVO(Decimal("0.001")),
        )
        self.assertEqual(changed.base_uom, UomCodeVO("KG"))
        self.assertEqual(changed.quantity_rules.step, Decimal("0.001"))
        self.assertEqual(serial.tracking_mode, TrackingMode.SERIAL)

    def test_invalid_final_state_leaves_original_unchanged(self) -> None:
        """Не публикует частично изменённую позицию при несовместимых параметрах."""
        item = make_item()
        with self.assertRaises(InventoryError):
            revise(
                item,
                sku=SkuVO("another"),
                tracking_mode=TrackingMode.SERIAL,
                base_uom=UomCodeVO("KG"),
            )
        self.assertEqual((item.sku.value, item.base_uom.value), ("item", "PCS"))
