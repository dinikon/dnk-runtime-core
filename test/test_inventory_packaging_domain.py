"""Независимые штрихкоды товара, форм-факторы и единицы содержимого упаковки."""

import unittest
from dataclasses import FrozenInstanceError, fields, replace
from decimal import Decimal
from uuid import uuid4

from src.modules.inventory.domain.error import (
    InvalidPackagingValueError,
    UnknownUomError,
    IncompatibleUomError,
    QuantityPrecisionError,
)
from src.modules.inventory.domain.value_object.quantity import QuantityVO
from src.modules.inventory.domain.value_object.quantity_rules import QuantityRulesVO
from src.modules.inventory.domain.inventory_item.aggregate import InventoryItem
from src.modules.inventory.domain.inventory_item.entity.item_barcode import ItemBarcode
from src.modules.inventory.domain.inventory_item.entity.item_packaging import (
    ItemPackaging,
)
from src.modules.inventory.domain.inventory_item.error import (
    InvalidInventoryItemValueError,
    InvalidPackagingQuantityError,
    InventoryItemComponentNotFoundError,
    InventoryItemConflictError,
)
from src.modules.inventory.domain.inventory_item.value_object.barcode import BarcodeVO
from src.modules.inventory.domain.inventory_item.value_object.identifier import (
    InventoryItemIdVO,
)
from src.modules.inventory.domain.inventory_item.value_object.item_barcode_id import (
    ItemBarcodeIdVO,
)
from src.modules.inventory.domain.inventory_item.value_object.item_packaging_id import (
    ItemPackagingIdVO,
)
from src.modules.inventory.domain.inventory_item.value_object.packaging_quantity import (
    PackagingQuantityVO,
)
from src.modules.inventory.domain.inventory_item.value_object.sku import SkuVO
from src.modules.inventory.domain.inventory_item.value_object.tracking_mode import (
    TrackingMode,
)
from src.modules.inventory.domain.packaging_type.aggregate import PackagingType
from src.modules.inventory.domain.packaging_type.error import InvalidPackagingTypeError
from src.modules.inventory.domain.packaging_type.value_object.identifier import (
    PackagingTypeIdVO,
)
from src.modules.inventory.domain.value_object.packaging_code import PackagingCodeVO
from src.modules.inventory.domain.value_object.packaging_name import PackagingNameVO
from src.modules.inventory.domain.value_object.uom_code import UomCodeVO


class PackagingTypeDomainTests(unittest.TestCase):
    """Проверяет пользовательский форм-фактор без ограничений единиц измерения."""

    def setUp(self) -> None:
        """Создаёт тип ящика с пользовательскими названием и кодом."""
        self.kind = PackagingType.create(
            identifier=PackagingTypeIdVO(uuid4()),
            code=PackagingCodeVO(" BOX "),
            name=PackagingNameVO(" Ящик "),
        )

    def test_configuration_restore_and_snapshot_are_immutable(self) -> None:
        """Сохраняет ID и предыдущие снимки при переименовании и деактивации."""
        snapshot = self.kind.snapshot()
        changed = (
            self.kind.rename(PackagingNameVO("Коробка"))
            .change_code(PackagingCodeVO("CARTON"))
            .deactivate()
        )
        self.assertEqual(changed.id, self.kind.id)
        self.assertEqual(snapshot.name.value, "Ящик")
        self.assertEqual(snapshot.code.value, "BOX")
        self.assertTrue(snapshot.is_active)
        self.assertFalse(changed.is_active)
        self.assertTrue(changed.activate().is_active)
        self.assertEqual(
            PackagingType.restore(
                identifier=changed.id,
                code=changed.code,
                name=changed.name,
                is_active=False,
            ),
            changed,
        )
        for obj in (self.kind, snapshot):
            with self.assertRaises(FrozenInstanceError):
                obj.is_active = False

    def test_factories_reject_untyped_configuration(self) -> None:
        """Проверяет собственные типы справочника при восстановлении и изменении."""
        values = dict(
            identifier=self.kind.id,
            code=self.kind.code,
            name=self.kind.name,
            is_active=True,
        )
        for changes in (
            {"identifier": InventoryItemIdVO(uuid4())},
            {"code": "BOX"},
            {"name": None},
            {"is_active": 1},
        ):
            with (
                self.subTest(changes=changes),
                self.assertRaises(InvalidPackagingTypeError),
            ):
                PackagingType.restore(**(values | changes))
        with self.assertRaises(InvalidPackagingTypeError):
            self.kind.rename(None)

    def test_packaging_values_require_text_and_positive_decimal(self) -> None:
        """Сохраняет дробное содержимое и отклоняет пустоту, float и нечисловые значения."""
        self.assertEqual(PackagingNameVO(" Канистра 5 л ").value, "Канистра 5 л")
        for factory in (PackagingCodeVO, PackagingNameVO):
            for value in (None, 12, "", "  ", "x\ny", "x\u200by"):
                with (
                    self.subTest(factory=factory, value=value),
                    self.assertRaises(InvalidPackagingValueError),
                ):
                    factory(value)
        self.assertEqual(PackagingQuantityVO(Decimal("0.125")).value, Decimal("0.125"))
        for value in (
            None,
            1,
            1.5,
            "12",
            Decimal(0),
            Decimal(-1),
            Decimal("NaN"),
            Decimal("sNaN"),
            Decimal("Infinity"),
        ):
            with (
                self.subTest(value=value),
                self.assertRaises(InvalidPackagingQuantityError),
            ):
                PackagingQuantityVO(value)


class InventoryPackagingDomainTests(unittest.TestCase):
    """Проверяет произвольные упаковки и их независимость от штрихкодов товара."""

    def setUp(self) -> None:
        """Готовит товар без упаковок и вариант ящика на 12 штук."""
        self.pcs = UomCodeVO("PCS")
        self.kind = PackagingType.create(
            identifier=PackagingTypeIdVO(uuid4()),
            code=PackagingCodeVO("BOX"),
            name=PackagingNameVO("Ящик"),
        )
        self.item = self.create_item()
        self.box = self.packaging()

    def create_item(self, **changes: object) -> InventoryItem:
        """Создаёт учётную позицию только с обязательными свойствами."""
        values = dict(
            identifier=InventoryItemIdVO(uuid4()),
            sku=SkuVO("VITAMINS"),
            base_uom=self.pcs,
            quantity_rules=(
                QuantityRulesVO(Decimal("0.001"), 3)
                if changes.get("base_uom", self.pcs) != self.pcs
                else QuantityRulesVO(Decimal(1), 0)
            ),
        )
        return InventoryItem.create(**(values | changes))

    def restore_item(self, item: InventoryItem, **changes: object) -> InventoryItem:
        """Восстанавливает полный снимок с явно переопределёнными свойствами."""
        values = dict(
            identifier=item.id,
            sku=item.sku,
            base_uom=item.base_uom,
            quantity_rules=item.quantity_rules,
            tracking_mode=item.tracking_mode,
            expiration_mode=item.expiration_mode,
            packagings=item.packagings,
            barcodes=item.barcodes,
        )
        return InventoryItem.restore(**(values | changes))

    def packaging(self, **changes: object) -> ItemPackaging:
        """Создаёт вариант с явной единицей содержимого."""
        values = dict(
            identifier=ItemPackagingIdVO(uuid4()),
            packaging_type_id=self.kind.id,
            code=PackagingCodeVO("BOX_12"),
            name=PackagingNameVO("Ящик 12 штук"),
            content_quantity=PackagingQuantityVO(Decimal(12)),
            content_uom=self.pcs,
        )
        return ItemPackaging.create(**(values | changes))

    def change_packaging(self, item: InventoryItem, **changes: object) -> InventoryItem:
        """Меняет существующий вариант, сохраняя его идентичность."""
        values = dict(
            identifier=self.box.id,
            packaging_type=self.kind.snapshot(),
            code=self.box.code,
            name=self.box.name,
            content_quantity=self.box.content_quantity,
            content_uom=self.box.content_uom,
        )
        return item.change_packaging(**(values | changes))

    def test_item_without_packaging_and_barcode_contract(self) -> None:
        """Создание и восстановление допускают пустые упаковки, штрихкод содержит только ID и код."""
        self.assertEqual(self.item.packagings, ())
        self.assertEqual(self.restore_item(self.item), self.item)
        self.assertNotIn(
            "base_packaging_id", [field.name for field in fields(InventoryItem)]
        )
        self.assertEqual(
            [field.name for field in fields(ItemBarcode)], ["id", "barcode"]
        )

    def test_barcode_is_independent_of_packaging_lifecycle(self) -> None:
        """Штрихкод товара не меняется при создании, изменении или удалении упаковки."""
        barcode = ItemBarcode.create(
            identifier=ItemBarcodeIdVO(uuid4()), barcode=BarcodeVO("VITAMINS")
        )
        item = self.item.add_barcode(barcode)
        added = item.add_packaging(self.box, packaging_type=self.kind.snapshot())
        changed = self.change_packaging(
            added, content_quantity=PackagingQuantityVO(Decimal(24))
        )
        self.assertEqual(changed.barcodes, item.barcodes)
        self.assertEqual(changed.remove_packaging(self.box.id), item)
        self.assertEqual(
            added.get_packaging(self.box.id).content_quantity.value, Decimal(12)
        )
        self.assertEqual(
            changed.get_packaging(self.box.id).content_quantity.value, Decimal(24)
        )

    def test_content_one_is_an_ordinary_removable_variant(self) -> None:
        """Количество 1 разрешено без специальной роли базовой упаковки."""
        single = self.packaging(content_quantity=PackagingQuantityVO(Decimal(1)))
        item = self.item.add_packaging(single, packaging_type=self.kind.snapshot())
        self.assertEqual(item.remove_packaging(single.id), self.item)

    def test_multiple_variants_of_one_form_factor(self) -> None:
        """Один форм-фактор поддерживает несколько вариантов товара с разным содержимым."""
        other = self.packaging(
            code=PackagingCodeVO("BOX_24"),
            content_quantity=PackagingQuantityVO(Decimal(24)),
        )
        item = self.item.add_packaging(
            self.box, packaging_type=self.kind.snapshot()
        ).add_packaging(other, packaging_type=self.kind.snapshot())
        self.assertEqual(
            tuple(value.content_quantity.value for value in item.packagings),
            (Decimal(12), Decimal(24)),
        )
        self.assertEqual(self.restore_item(item), item)

    def test_form_factor_can_be_used_with_different_base_units(self) -> None:
        """Единица содержимого определяется товаром, а не типом тары."""
        for code in ("PCS", "L", "KG"):
            with self.subTest(code=code):
                uom = UomCodeVO(code)
                item = self.create_item(base_uom=uom)
                packaging = self.packaging(content_uom=uom)
                item = item.add_packaging(
                    packaging, packaging_type=self.kind.snapshot()
                )
                self.assertEqual(item.packagings[0].content_uom, uom)

    def test_standard_content_unit_is_available_without_item_conversions(self) -> None:
        """500 мл разрешены для литрового товара без настройки множителя пользователем."""
        item = self.create_item(base_uom=UomCodeVO("L"))
        packaging = self.packaging(
            content_quantity=PackagingQuantityVO(Decimal(500)),
            content_uom=UomCodeVO("ML"),
        )
        item = item.add_packaging(packaging, packaging_type=self.kind.snapshot())
        self.assertEqual(self.restore_item(item), item)
        quantity = item.to_base_quantity(
            quantity=QuantityVO(packaging.content_quantity.value),
            uom=packaging.content_uom,
        )
        self.assertEqual(quantity.value, Decimal("0.5"))
        self.assertEqual(item.remove_packaging(packaging.id).packagings, ())

    def test_serial_packaging_requires_integral_content_at_every_write_path(
        self,
    ) -> None:
        """Серийный товар допускает ящик из 12 штук и запрещает дробное содержимое."""
        for mode in (TrackingMode.SERIAL, TrackingMode.LOT_AND_SERIAL):
            with self.subTest(mode=mode):
                empty = self.create_item(tracking_mode=mode)
                item = empty.add_packaging(
                    self.box, packaging_type=self.kind.snapshot()
                )
                self.assertEqual(self.restore_item(item), item)
                invalid = self.packaging(
                    content_quantity=PackagingQuantityVO(Decimal("0.5"))
                )
                with self.assertRaises(QuantityPrecisionError):
                    empty.add_packaging(invalid, packaging_type=self.kind.snapshot())
                with self.assertRaises(QuantityPrecisionError):
                    self.restore_item(empty, packagings=(invalid,))
                with self.assertRaises(QuantityPrecisionError):
                    self.change_packaging(
                        item, content_quantity=invalid.content_quantity
                    )
                self.assertEqual(empty.packagings, ())
                self.assertEqual(item.packagings, (self.box,))

    def test_incompatible_dimensions_are_rejected_on_add_change_and_restore(
        self,
    ) -> None:
        """Масса упаковки не заменяет объём товара без отдельного правила плотности."""
        item = self.create_item(base_uom=UomCodeVO("L"))
        invalid = self.packaging(content_uom=UomCodeVO("KG"))
        with self.assertRaises(IncompatibleUomError):
            item.add_packaging(invalid, packaging_type=self.kind.snapshot())
        with self.assertRaises(IncompatibleUomError):
            self.restore_item(item, packagings=(invalid,))
        packaging = self.packaging(content_uom=UomCodeVO("ML"))
        item = item.add_packaging(packaging, packaging_type=self.kind.snapshot())
        with self.assertRaises(IncompatibleUomError):
            self.change_packaging(
                item, identifier=packaging.id, content_uom=UomCodeVO("KG")
            )
        self.assertEqual(item.packagings, (packaging,))

    def test_unknown_content_unit_rejected_on_add_change_and_restore(self) -> None:
        """Все пути записи отклоняют единицу, отсутствующую в системном справочнике."""
        unknown = UomCodeVO("UNKNOWN")
        invalid = self.packaging(content_uom=unknown)
        with self.assertRaises(UnknownUomError):
            self.item.add_packaging(invalid, packaging_type=self.kind.snapshot())
        with self.assertRaises(UnknownUomError):
            self.restore_item(self.item, packagings=(invalid,))
        item = self.item.add_packaging(self.box, packaging_type=self.kind.snapshot())
        with self.assertRaises(UnknownUomError):
            self.change_packaging(item, content_uom=unknown)
        self.assertEqual(item.packagings, (self.box,))

    def test_duplicate_ids_and_codes_rejected_on_add_change_and_restore(self) -> None:
        """Проверяет уникальность вариантов без изменения исходного агрегата."""
        item = self.item.add_packaging(self.box, packaging_type=self.kind.snapshot())
        for duplicate in (self.box, replace(self.box, id=ItemPackagingIdVO(uuid4()))):
            with self.subTest(duplicate=duplicate):
                with self.assertRaises(InventoryItemConflictError):
                    item.add_packaging(duplicate, packaging_type=self.kind.snapshot())
                with self.assertRaises(InventoryItemConflictError):
                    self.restore_item(item, packagings=(*item.packagings, duplicate))
        other = self.packaging(code=PackagingCodeVO("OTHER"))
        item = item.add_packaging(other, packaging_type=self.kind.snapshot())
        with self.assertRaises(InventoryItemConflictError):
            self.change_packaging(item, identifier=other.id, code=self.box.code)
        self.assertEqual(item.packagings, (self.box, other))

    def test_assignment_requires_active_matching_type_snapshot(self) -> None:
        """Проверяет активность и совпадение ID типа при новом назначении."""
        with self.assertRaises(InventoryItemConflictError):
            self.item.add_packaging(
                self.box, packaging_type=self.kind.deactivate().snapshot()
            )
        wrong = replace(self.kind.snapshot(), id=PackagingTypeIdVO(uuid4()))
        with self.assertRaises(InventoryItemConflictError):
            self.item.add_packaging(self.box, packaging_type=wrong)
        for snapshot in (self.kind, None, replace(self.kind.snapshot(), is_active=1)):
            with (
                self.subTest(snapshot=snapshot),
                self.assertRaises(InvalidInventoryItemValueError),
            ):
                self.item.add_packaging(self.box, packaging_type=snapshot)
        item = self.item.add_packaging(self.box, packaging_type=self.kind.snapshot())
        with self.assertRaises(InventoryItemConflictError):
            self.change_packaging(
                item, packaging_type=self.kind.deactivate().snapshot()
            )
        self.assertEqual(self.restore_item(item), item)

    def test_foreign_variant_ids_cannot_be_changed_or_removed(self) -> None:
        """Не позволяет изменять упаковку, отсутствующую в данном товаре."""
        foreign = ItemPackagingIdVO(uuid4())
        for action in (
            lambda: self.item.get_packaging(foreign),
            lambda: self.item.remove_packaging(foreign),
            lambda: self.change_packaging(self.item, identifier=foreign),
        ):
            with self.assertRaises(InventoryItemComponentNotFoundError):
                action()

    def test_restore_revalidates_entity_types(self) -> None:
        """Восстановление не пропускает изменяемые коллекции и сырые значения содержимого."""
        for values in (
            [],
            (object(),),
            (replace(self.box, content_quantity=Decimal(12)),),
            (replace(self.box, content_uom="PCS"),),
        ):
            with (
                self.subTest(values=values),
                self.assertRaises(InvalidInventoryItemValueError),
            ):
                self.restore_item(self.item, packagings=values)

    def test_entity_factories_and_immutable_content(self) -> None:
        """Фабрики требуют типизированные значения и сохраняют явную единицу содержимого."""
        values = dict(
            identifier=self.box.id,
            packaging_type_id=self.kind.id,
            code=self.box.code,
            name=self.box.name,
            content_quantity=self.box.content_quantity,
            content_uom=self.pcs,
        )
        for factory in (ItemPackaging.create, ItemPackaging.restore):
            self.assertEqual(factory(**values), self.box)
            for changes in (
                {"identifier": self.kind.id},
                {"packaging_type_id": self.box.id},
                {"content_quantity": Decimal(12)},
                {"content_uom": "PCS"},
            ):
                with (
                    self.subTest(factory=factory, changes=changes),
                    self.assertRaises(InvalidInventoryItemValueError),
                ):
                    factory(**(values | changes))
        for obj, field, value in (
            (self.box, "content_uom", UomCodeVO("L")),
            (self.box.content_quantity, "value", Decimal(24)),
        ):
            with (
                self.subTest(obj=obj, field=field),
                self.assertRaises(FrozenInstanceError),
            ):
                setattr(obj, field, value)
