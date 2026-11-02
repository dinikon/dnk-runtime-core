"""Проверки ручной номенклатуры, неизменяемого состава и настроек прослеживаемости."""

import unittest
from dataclasses import FrozenInstanceError, replace
from decimal import Decimal
from uuid import uuid4

from src.modules.inventory.domain.aggregate import InventoryItem
from src.modules.inventory.domain.entity.item_barcode import ItemBarcode
from src.modules.inventory.domain.entity.item_uom_conversion import ItemUomConversion
from src.modules.inventory.domain.error import (
    InvalidBarcodeError,
    InvalidConversionFactorError,
    InvalidInventoryItemValueError,
    InvalidSkuError,
    InvalidTrackingConfigurationError,
    InvalidUomCodeError,
    InventoryItemComponentNotFoundError,
    InventoryItemConflictError,
    UnknownUomError,
)
from src.modules.inventory.domain.value_object.barcode import BarcodeVO
from src.modules.inventory.domain.value_object.conversion_factor import (
    ConversionFactorVO,
)
from src.modules.inventory.domain.value_object.expiration_mode import ExpirationMode
from src.modules.inventory.domain.value_object.identifier import InventoryItemIdVO
from src.modules.inventory.domain.value_object.item_barcode_id import ItemBarcodeIdVO
from src.modules.inventory.domain.value_object.item_uom_conversion_id import (
    ItemUomConversionIdVO,
)
from src.modules.inventory.domain.value_object.sku import SkuVO
from src.modules.inventory.domain.value_object.tracking_mode import TrackingMode
from src.modules.inventory.domain.value_object.uom_code import UomCodeVO


class InventoryValueObjectTests(unittest.TestCase):
    """Проверяет нормализацию кодов и точность значений конвертации."""

    def test_text_values_trim_without_losing_identity(self) -> None:
        """Сохраняет регистр SKU и ведущие нули штрихкода после trim."""
        self.assertEqual(SkuVO("  SKU-a  ").value, "SKU-a")
        self.assertNotEqual(SkuVO("SKU-a"), SkuVO("SKU-A"))
        self.assertEqual(UomCodeVO(" PCS ").value, "PCS")
        self.assertEqual(BarcodeVO(" 000123 ").value, "000123")
        self.assertEqual(SkuVO("Артикул/123").value, "Артикул/123")

    def test_invalid_text_is_rejected_with_domain_errors(self) -> None:
        """Отклоняет отсутствие, пустоту, неверные типы и управляющие символы."""
        for factory, error in (
            (SkuVO, InvalidSkuError),
            (UomCodeVO, InvalidUomCodeError),
            (BarcodeVO, InvalidBarcodeError),
        ):
            for value in (None, 123, "", "   ", "a\nb", "a\x7fb", "a\u200bb", "x\t"):
                with self.subTest(factory=factory, value=value):
                    with self.assertRaises(error):
                        factory(value)

    def test_factor_preserves_decimal_precision(self) -> None:
        """Принимает положительные дробные коэффициенты без округления."""
        for value in (
            Decimal("12"),
            Decimal("0.001"),
            Decimal("1.1234567890123456789"),
        ):
            with self.subTest(value=value):
                self.assertEqual(ConversionFactorVO(value).value, value)

    def test_factor_rejects_zero_negative_nonfinite_and_float(self) -> None:
        """Не допускает недостоверные и неявно преобразованные коэффициенты."""
        for value in (
            Decimal(0),
            Decimal("-1"),
            Decimal("NaN"),
            Decimal("sNaN"),
            Decimal("Infinity"),
            Decimal("-Infinity"),
            1,
            1.5,
            "12",
            None,
        ):
            with (
                self.subTest(value=value),
                self.assertRaises(InvalidConversionFactorError),
            ):
                ConversionFactorVO(value)


class InventoryItemDomainTests(unittest.TestCase):
    """Проверяет границы агрегата через фабрики и публичные доменные операции."""

    def setUp(self) -> None:
        """Готовит позицию, штуку и коробку с независимыми дочерними ID."""
        self.identifier = InventoryItemIdVO(uuid4())
        self.pcs = UomCodeVO("PCS")
        self.box = UomCodeVO("BOX")
        self.conversion = ItemUomConversion.create(
            identifier=ItemUomConversionIdVO(uuid4()),
            uom=self.box,
            factor=ConversionFactorVO(Decimal(12)),
        )
        self.barcode = ItemBarcode.create(
            identifier=ItemBarcodeIdVO(uuid4()),
            barcode=BarcodeVO("000123"),
            uom=self.box,
        )
        self.item = self.make_item()

    def make_item(self, **changes: object) -> InventoryItem:
        """Создаёт корректный агрегат с явно переопределёнными параметрами."""
        values = dict(
            identifier=self.identifier,
            sku=SkuVO("SKU-001"),
            base_uom=self.pcs,
            tracking_mode=TrackingMode.LOT,
            expiration_mode=ExpirationMode.REQUIRED,
            barcodes=(self.barcode,),
            uom_conversions=(self.conversion,),
        )
        values.update(changes)
        return InventoryItem.create(**values)

    def restore_item(self, **changes: object) -> InventoryItem:
        """Восстанавливает полный снимок с явно переопределённым состоянием."""
        values = dict(
            identifier=self.item.id,
            sku=self.item.sku,
            base_uom=self.item.base_uom,
            tracking_mode=self.item.tracking_mode,
            expiration_mode=self.item.expiration_mode,
            barcodes=self.item.barcodes,
            uom_conversions=self.item.uom_conversions,
        )
        values.update(changes)
        return InventoryItem.restore(**values)

    def test_create_defaults_and_empty_collections(self) -> None:
        """Создаёт минимальную позицию только с обязательными ручными данными."""
        item = InventoryItem.create(
            identifier=self.identifier, sku=SkuVO("MANUAL"), base_uom=self.pcs
        )
        self.assertEqual(item.sku, SkuVO("MANUAL"))
        self.assertIs(item.tracking_mode, TrackingMode.NONE)
        self.assertIs(item.expiration_mode, ExpirationMode.DISABLED)
        self.assertEqual((item.barcodes, item.uom_conversions), ((), ()))

    def test_restore_preserves_the_full_state_and_child_identity(self) -> None:
        """Восстанавливает данные без генерации или замены идентификаторов."""
        restored = self.restore_item()
        self.assertEqual(restored, self.item)
        self.assertIs(restored.barcodes[0].id, self.barcode.id)
        self.assertIs(restored.uom_conversions[0].id, self.conversion.id)

    def test_factories_enforce_tracking_expiration_matrix(self) -> None:
        """Разрешает независимые настройки и запрещает REQUIRED без прослеживаемости."""
        for factory in (self.make_item, self.restore_item):
            for tracking in TrackingMode:
                for expiration in ExpirationMode:
                    with self.subTest(
                        factory=factory, tracking=tracking, expiration=expiration
                    ):
                        if (
                            tracking is TrackingMode.NONE
                            and expiration is ExpirationMode.REQUIRED
                        ):
                            with self.assertRaises(InvalidTrackingConfigurationError):
                                factory(
                                    tracking_mode=tracking, expiration_mode=expiration
                                )
                        else:
                            item = factory(
                                tracking_mode=tracking, expiration_mode=expiration
                            )
                            self.assertIs(item.expiration_mode, expiration)

    def test_factories_require_typed_manual_state(self) -> None:
        """Отклоняет отсутствие SKU, чужие ID, сырые режимы и изменяемые коллекции."""
        for factory in (self.make_item, self.restore_item):
            for changes in (
                {"sku": None},
                {"sku": "MANUAL"},
                {"base_uom": None},
                {"identifier": self.barcode.id},
                {"tracking_mode": "LOT"},
                {"expiration_mode": "OPTIONAL"},
                {"barcodes": []},
                {"uom_conversions": []},
                {"barcodes": (object(),)},
                {"uom_conversions": (object(),)},
            ):
                with self.subTest(factory=factory, changes=changes):
                    with self.assertRaises(InvalidInventoryItemValueError):
                        factory(**changes)

    def test_factories_reject_duplicate_child_ids_values_and_units(self) -> None:
        """Проверяет уникальность всего состава и при создании, и при восстановлении."""
        cases = (
            {
                "barcodes": (
                    self.barcode,
                    replace(self.barcode, barcode=BarcodeVO("456")),
                )
            },
            {
                "barcodes": (
                    self.barcode,
                    replace(self.barcode, id=ItemBarcodeIdVO(uuid4())),
                )
            },
            {
                "uom_conversions": (
                    self.conversion,
                    replace(self.conversion, uom=UomCodeVO("PACK")),
                )
            },
            {
                "uom_conversions": (
                    self.conversion,
                    replace(self.conversion, id=ItemUomConversionIdVO(uuid4())),
                )
            },
            {"uom_conversions": (replace(self.conversion, uom=self.pcs),)},
        )
        for factory in (self.make_item, self.restore_item):
            for changes in cases:
                with self.subTest(factory=factory, changes=changes):
                    with self.assertRaises(InventoryItemConflictError):
                        factory(**changes)

    def test_factories_check_child_values_even_if_constructor_was_used_directly(
        self,
    ) -> None:
        """Не позволяет сохранить Entity с неверными собственными типами."""
        for factory in (self.make_item, self.restore_item):
            for changes in (
                {"barcodes": (replace(self.barcode, barcode="000123"),)},
                {"uom_conversions": (replace(self.conversion, factor=Decimal(12)),)},
            ):
                with self.subTest(factory=factory, changes=changes):
                    with self.assertRaises(InvalidInventoryItemValueError):
                        factory(**changes)

    def test_barcode_requires_a_declared_uom_at_both_factories(self) -> None:
        """Не допускает единицу штрихкода без базовой единицы или конвертации."""
        for factory in (self.make_item, self.restore_item):
            with self.subTest(factory=factory), self.assertRaises(UnknownUomError):
                factory(uom_conversions=())

    def test_change_sku_preserves_identity_and_original_state(self) -> None:
        """Меняет ручной SKU только у нового экземпляра с прежним ID и составом."""
        changed = self.item.change_sku(SkuVO(" replacement "))
        self.assertEqual(changed.sku.value, "replacement")
        self.assertEqual(changed.id, self.item.id)
        self.assertEqual(changed.barcodes, self.item.barcodes)
        self.assertEqual(self.item.sku.value, "SKU-001")
        with self.assertRaises(InvalidInventoryItemValueError):
            self.item.change_sku(None)
        self.assertEqual(self.item.sku.value, "SKU-001")

    def test_barcode_lifecycle_is_controlled_by_the_aggregate(self) -> None:
        """Добавляет, меняет и удаляет штрихкод с сохранением его ID."""
        barcode = ItemBarcode.create(
            identifier=ItemBarcodeIdVO(uuid4()),
            barcode=BarcodeVO("000456"),
            uom=self.pcs,
        )
        added = self.item.add_barcode(barcode)
        changed = added.change_barcode(
            identifier=barcode.id, barcode=BarcodeVO("000789"), uom=self.box
        )
        self.assertEqual(changed.barcodes[-1].id, barcode.id)
        self.assertEqual(changed.barcodes[-1].barcode.value, "000789")
        self.assertEqual(changed.barcodes[-1].uom, self.box)
        self.assertEqual(changed.remove_barcode(barcode.id), self.item)
        self.assertEqual(self.item.barcodes, (self.barcode,))

    def test_invalid_barcode_changes_leave_original_composition_intact(self) -> None:
        """Отклоняет дубликаты и неизвестные единицы без частичных изменений."""
        other = replace(
            self.barcode, id=ItemBarcodeIdVO(uuid4()), barcode=BarcodeVO("456")
        )
        item = self.item.add_barcode(other)
        for action in (
            lambda: item.add_barcode(other),
            lambda: item.change_barcode(
                identifier=other.id, barcode=self.barcode.barcode, uom=self.pcs
            ),
        ):
            with self.assertRaises(InventoryItemConflictError):
                action()
            self.assertEqual(item.barcodes, (self.barcode, other))
        with self.assertRaises(UnknownUomError):
            item.change_barcode(
                identifier=other.id, barcode=other.barcode, uom=UomCodeVO("UNKNOWN")
            )
        self.assertEqual(item.barcodes, (self.barcode, other))

    def test_conversion_lifecycle_preserves_id_and_decimal_factor(self) -> None:
        """Добавляет, меняет и удаляет прямую конвертацию агрегата."""
        conversion = replace(
            self.conversion, id=ItemUomConversionIdVO(uuid4()), uom=UomCodeVO("PACK")
        )
        added = self.item.add_uom_conversion(conversion)
        changed = added.change_uom_conversion(
            identifier=conversion.id,
            uom=UomCodeVO("BAG"),
            factor=ConversionFactorVO(Decimal("0.125")),
        )
        self.assertEqual(changed.uom_conversions[-1].id, conversion.id)
        self.assertEqual(changed.uom_conversions[-1].factor.value, Decimal("0.125"))
        self.assertEqual(changed.remove_uom_conversion(conversion.id), self.item)
        self.assertEqual(self.item.uom_conversions, (self.conversion,))

    def test_used_conversion_cannot_be_removed_or_renamed(self) -> None:
        """Защищает ссылки штрихкодов на единицу конвертации."""
        with self.assertRaises(InventoryItemConflictError):
            self.item.remove_uom_conversion(self.conversion.id)
        with self.assertRaises(UnknownUomError):
            self.item.change_uom_conversion(
                identifier=self.conversion.id,
                uom=UomCodeVO("PACK"),
                factor=self.conversion.factor,
            )
        self.assertEqual(self.item.uom_conversions, (self.conversion,))
        changed = self.item.change_uom_conversion(
            identifier=self.conversion.id,
            uom=self.box,
            factor=ConversionFactorVO(Decimal(24)),
        )
        self.assertEqual(changed.uom_conversions[0].factor.value, Decimal(24))
        self.assertEqual(self.item.uom_conversions[0].factor.value, Decimal(12))
        self.assertEqual(
            self.item.remove_barcode(self.barcode.id)
            .remove_uom_conversion(self.conversion.id)
            .uom_conversions,
            (),
        )

    def test_duplicate_and_base_conversions_are_rejected_during_changes(self) -> None:
        """Не допускает дубликаты единиц, ID и конвертацию базовой единицы."""
        for conversion in (
            self.conversion,
            replace(self.conversion, id=ItemUomConversionIdVO(uuid4())),
            replace(self.conversion, id=ItemUomConversionIdVO(uuid4()), uom=self.pcs),
        ):
            with (
                self.subTest(conversion=conversion),
                self.assertRaises(InventoryItemConflictError),
            ):
                self.item.add_uom_conversion(conversion)
        other = replace(
            self.conversion, id=ItemUomConversionIdVO(uuid4()), uom=UomCodeVO("PACK")
        )
        item = self.item.add_uom_conversion(other)
        with self.assertRaises(InventoryItemConflictError):
            item.change_uom_conversion(
                identifier=other.id, uom=self.box, factor=other.factor
            )
        self.assertEqual(item.uom_conversions, (self.conversion, other))

    def test_foreign_children_cannot_be_changed_or_removed(self) -> None:
        """Отклоняет попытки изменения Entity, не принадлежащих позиции."""
        barcode_id = ItemBarcodeIdVO(uuid4())
        conversion_id = ItemUomConversionIdVO(uuid4())
        for action in (
            lambda: self.item.remove_barcode(barcode_id),
            lambda: self.item.change_barcode(
                identifier=barcode_id, barcode=self.barcode.barcode, uom=self.pcs
            ),
            lambda: self.item.remove_uom_conversion(conversion_id),
            lambda: self.item.change_uom_conversion(
                identifier=conversion_id, uom=self.box, factor=self.conversion.factor
            ),
        ):
            with self.assertRaises(InventoryItemComponentNotFoundError):
                action()

    def test_aggregate_entities_and_values_are_immutable(self) -> None:
        """Защищает ID, настройки и дочерние данные от прямого присваивания."""
        for obj, name, value in (
            (self.item, "id", InventoryItemIdVO(uuid4())),
            (self.item, "base_uom", self.box),
            (self.item, "tracking_mode", TrackingMode.SERIAL),
            (self.item, "expiration_mode", ExpirationMode.DISABLED),
            (self.item, "barcodes", ()),
            (self.barcode, "uom", self.pcs),
            (self.conversion, "factor", ConversionFactorVO(Decimal(24))),
            (self.item.sku, "value", "CHANGED"),
        ):
            with (
                self.subTest(obj=obj, name=name),
                self.assertRaises(FrozenInstanceError),
            ):
                setattr(obj, name, value)

    def test_entity_factories_restore_valid_values_and_reject_foreign_id_types(
        self,
    ) -> None:
        """Проверяет собственные фабрики Entity независимо от состава агрегата."""
        for factory in (ItemBarcode.create, ItemBarcode.restore):
            self.assertEqual(
                factory(
                    identifier=self.barcode.id,
                    barcode=self.barcode.barcode,
                    uom=self.box,
                ),
                self.barcode,
            )
            with self.assertRaises(InvalidInventoryItemValueError):
                factory(
                    identifier=self.identifier,
                    barcode=self.barcode.barcode,
                    uom=self.box,
                )
        for factory in (ItemUomConversion.create, ItemUomConversion.restore):
            self.assertEqual(
                factory(
                    identifier=self.conversion.id,
                    uom=self.box,
                    factor=self.conversion.factor,
                ),
                self.conversion,
            )
            with self.assertRaises(InvalidInventoryItemValueError):
                factory(
                    identifier=self.barcode.id,
                    uom=self.box,
                    factor=self.conversion.factor,
                )
