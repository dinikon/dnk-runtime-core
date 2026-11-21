"""Проверки ручной номенклатуры, неизменяемого состава и настроек прослеживаемости."""

import unittest
from dataclasses import FrozenInstanceError, fields, replace
from decimal import Decimal
from uuid import uuid4

from src.modules.inventory.domain.inventory_item.aggregate import InventoryItem
from src.modules.inventory.domain.error import (
    InvalidUomCodeError,
    QuantityStepError,
    UnknownUomError,
)
from src.modules.inventory.domain.inventory_item.entity.item_barcode import ItemBarcode
from src.modules.inventory.domain.inventory_item.error import (
    InvalidBarcodeError,
    InvalidInventoryItemValueError,
    InvalidSkuError,
    InvalidTrackingConfigurationError,
    InventoryItemComponentNotFoundError,
    InventoryItemConflictError,
)
from src.modules.inventory.domain.inventory_item.value_object.barcode import BarcodeVO
from src.modules.inventory.domain.inventory_item.value_object.expiration_mode import (
    ExpirationMode,
)
from src.modules.inventory.domain.inventory_item.value_object.identifier import (
    InventoryItemIdVO,
)
from src.modules.inventory.domain.inventory_item.value_object.item_barcode_id import (
    ItemBarcodeIdVO,
)
from src.modules.inventory.domain.inventory_item.value_object.sku import SkuVO
from src.modules.inventory.domain.inventory_item.value_object.tracking_mode import (
    TrackingMode,
)
from src.modules.inventory.domain.value_object.uom_code import UomCodeVO
from src.modules.inventory.domain.value_object.quantity_rules import QuantityRulesVO
from src.modules.inventory.domain.value_object.quantity import QuantityVO
from src.modules.inventory.domain.uom_catalog import list_uoms


class InventoryValueObjectTests(unittest.TestCase):
    """Проверяет нормализацию кодов и режим необязательных дат-заметок."""

    def test_serial_requirement_includes_combined_tracking_mode(self) -> None:
        """Оба режима серий требуют поштучной идентификации; NONE и LOT её не требуют."""
        for mode, expected in (
            (TrackingMode.NONE, False),
            (TrackingMode.LOT, False),
            (TrackingMode.SERIAL, True),
            (TrackingMode.LOT_AND_SERIAL, True),
        ):
            with self.subTest(mode=mode):
                self.assertIs(mode.requires_serial, expected)

    def test_text_values_trim_without_losing_identity(self) -> None:
        """Нормализует регистр SKU, сохраняя ведущие нули и регистр штрихкода."""
        self.assertEqual(SkuVO("  SKU-a  ").value, "sku-a")
        self.assertEqual(SkuVO("SKU-a"), SkuVO("SKU-A"))
        self.assertEqual(hash(SkuVO("ABC")), hash(SkuVO("abc")))
        self.assertEqual(len({SkuVO("ABC"), SkuVO(" abc ")}), 1)
        self.assertEqual(UomCodeVO(" PCS ").value, "PCS")
        self.assertEqual(BarcodeVO(" 000123 ").value, "000123")
        self.assertEqual(SkuVO("Артикул/123").value, "артикул/123")
        self.assertNotEqual(BarcodeVO("ABC"), BarcodeVO("abc"))

    def test_sku_length_limit_applies_to_the_canonical_value(self) -> None:
        """Принимает 25 символов после trim и учитывает расширение Unicode casefold."""
        self.assertEqual(SkuVO(" " + "A" * 25 + " ").value, "a" * 25)
        self.assertEqual(SkuVO("Straße"), SkuVO("STRASSE"))
        self.assertEqual(SkuVO("A" * 23 + "ß").value, "a" * 23 + "ss")
        for value in ("A" * 26, "A" * 24 + "ß"):
            with self.subTest(value=value), self.assertRaises(InvalidSkuError):
                SkuVO(value)

    def test_optional_expiration_preserves_its_note_mode_without_date_control(
        self,
    ) -> None:
        """Различает режим заметок и NONE при одинаково выключенном контроле дат."""
        self.assertIsNot(ExpirationMode.NONE, ExpirationMode.OPTIONAL)
        self.assertEqual(ExpirationMode("OPTIONAL"), ExpirationMode.OPTIONAL)
        self.assertFalse(ExpirationMode.NONE.controls_expiration)
        self.assertFalse(ExpirationMode.OPTIONAL.controls_expiration)
        self.assertTrue(ExpirationMode.REQUIRED.controls_expiration)

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


class InventoryItemDomainTests(unittest.TestCase):
    """Проверяет границы агрегата через фабрики и публичные доменные операции."""

    def setUp(self) -> None:
        """Готовит позицию, штуку и дюжину с независимыми дочерними ID."""
        self.identifier = InventoryItemIdVO(uuid4())
        self.pcs = UomCodeVO("PCS")
        self.barcode = ItemBarcode.create(
            identifier=ItemBarcodeIdVO(uuid4()),
            barcode=BarcodeVO("000123"),
        )
        self.item = self.make_item()

    def make_item(self, **changes: object) -> InventoryItem:
        """Создаёт корректный агрегат с явно переопределёнными параметрами."""
        values = dict(
            identifier=self.identifier,
            sku=SkuVO("SKU-001"),
            base_uom=self.pcs,
            quantity_rules=QuantityRulesVO(Decimal(1)),
            tracking_mode=TrackingMode.LOT,
            expiration_mode=ExpirationMode.REQUIRED,
            barcodes=(self.barcode,),
        )
        values.update(changes)
        return InventoryItem.create(**values)

    def restore_item(self, **changes: object) -> InventoryItem:
        """Восстанавливает полный снимок с явно переопределённым состоянием."""
        values = dict(
            identifier=self.item.id,
            sku=self.item.sku,
            base_uom=self.item.base_uom,
            quantity_rules=self.item.quantity_rules,
            packagings=self.item.packagings,
            tracking_mode=self.item.tracking_mode,
            expiration_mode=self.item.expiration_mode,
            barcodes=self.item.barcodes,
        )
        values.update(changes)
        return InventoryItem.restore(**values)

    def test_create_defaults_and_empty_collections(self) -> None:
        """Создаёт минимальную позицию только с обязательными ручными данными."""
        item = InventoryItem.create(
            identifier=self.identifier,
            sku=SkuVO("MANUAL"),
        )
        self.assertEqual(item.sku, SkuVO("MANUAL"))
        self.assertEqual(item.base_uom, UomCodeVO("PCS"))
        self.assertEqual(item.quantity_rules, QuantityRulesVO(Decimal("1")))
        self.assertIs(item.tracking_mode, TrackingMode.NONE)
        self.assertIs(item.expiration_mode, ExpirationMode.NONE)
        self.assertEqual((item.barcodes, item.packagings), ((), ()))

    def test_create_defaults_are_independent_and_explicit_values_take_priority(
        self,
    ) -> None:
        """Дополняет только пропущенные настройки и проверяет совместимость результата."""
        mass = InventoryItem.create(
            identifier=self.identifier, sku=SkuVO("mass"), base_uom=UomCodeVO("KG")
        )
        self.assertEqual(mass.base_uom, UomCodeVO("KG"))
        self.assertEqual(mass.quantity_rules.step, Decimal("1"))
        fractional = InventoryItem.create(
            identifier=self.identifier,
            sku=SkuVO("fractional"),
            quantity_rules=QuantityRulesVO(Decimal("0.125")),
        )
        self.assertEqual(fractional.base_uom, self.pcs)
        self.assertEqual(fractional.quantity_rules.step, Decimal("0.125"))
        serial = InventoryItem.create(
            identifier=self.identifier,
            sku=SkuVO("serial"),
            tracking_mode=TrackingMode.LOT_AND_SERIAL,
            expiration_mode=ExpirationMode.REQUIRED,
        )
        self.assertEqual(serial.base_uom, self.pcs)
        self.assertEqual(serial.quantity_rules.step, Decimal("1"))
        self.assertEqual(serial.tracking_mode, TrackingMode.LOT_AND_SERIAL)
        self.assertEqual(serial.expiration_mode, ExpirationMode.REQUIRED)
        with self.assertRaises(InvalidTrackingConfigurationError):
            InventoryItem.create(
                identifier=self.identifier,
                sku=SkuVO("invalid"),
                base_uom=UomCodeVO("KG"),
                tracking_mode=TrackingMode.SERIAL,
            )
        with self.assertRaises(InvalidTrackingConfigurationError):
            InventoryItem.create(
                identifier=self.identifier,
                sku=SkuVO("invalid"),
                expiration_mode=ExpirationMode.REQUIRED,
            )

    def test_restore_preserves_the_full_state_and_child_identity(self) -> None:
        """Восстанавливает данные без генерации или замены идентификаторов."""
        restored = self.restore_item()
        self.assertEqual(restored, self.item)
        self.assertIs(restored.barcodes[0].id, self.barcode.id)

    def test_optional_expiration_survives_restore_and_changes_without_tracking(
        self,
    ) -> None:
        """Сохраняет необязательные заметки при выключенном контроле дат и NONE tracking."""
        for factory in (self.make_item, self.restore_item):
            with self.subTest(factory=factory):
                item = factory(
                    tracking_mode=TrackingMode.NONE,
                    expiration_mode=ExpirationMode.OPTIONAL,
                )
                changed = item.change_sku(SkuVO("Another-SKU"))
                self.assertIs(changed.expiration_mode, ExpirationMode.OPTIONAL)
                self.assertIs(changed.tracking_mode, TrackingMode.NONE)
                self.assertFalse(changed.expiration_mode.controls_expiration)

    def test_sku_equality_uses_the_same_canonical_form_at_factories_and_changes(
        self,
    ) -> None:
        """Сохраняет единый SKU при разных регистрах ввода, восстановлении и замене."""
        for factory in (self.make_item, self.restore_item):
            with self.subTest(factory=factory):
                item = factory(sku=SkuVO(" AbC "))
                changed = item.change_sku(SkuVO("aBc"))
                self.assertEqual(changed, item)
                self.assertEqual(changed.sku.value, "abc")

    def test_factories_enforce_tracking_expiration_matrix(self) -> None:
        """Разрешает независимые настройки и запрещает REQUIRED без прослеживаемости."""
        for factory in (self.make_item, self.restore_item):
            for tracking in TrackingMode:
                for expiration in ExpirationMode:
                    with self.subTest(
                        factory=factory, tracking=tracking, expiration=expiration
                    ):
                        if (
                            tracking in (TrackingMode.NONE, TrackingMode.SERIAL)
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

    def test_factories_enforce_tracking_unit_rules_and_expiration_matrix(self) -> None:
        """Проверяет все системные единицы и режимы с допустимыми и конфликтными настройками."""
        configurations = (
            (QuantityRulesVO(Decimal("1")), True),
            (QuantityRulesVO(Decimal("1.000")), True),
            (QuantityRulesVO(Decimal("0.5")), False),
            (QuantityRulesVO(Decimal("0.001")), False),
            (QuantityRulesVO(Decimal("2")), False),
        )
        for factory in (self.make_item, self.restore_item):
            for tracking in TrackingMode:
                for unit in list_uoms():
                    for rules, serial_compatible in configurations:
                        for expiration in ExpirationMode:
                            values = dict(
                                tracking_mode=tracking,
                                base_uom=unit.code,
                                quantity_rules=rules,
                                expiration_mode=expiration,
                            )
                            with self.subTest(factory=factory, **values):
                                if (
                                    tracking in (TrackingMode.NONE, TrackingMode.SERIAL)
                                    and expiration is ExpirationMode.REQUIRED
                                ):
                                    allowed = False
                                elif tracking in (TrackingMode.NONE, TrackingMode.LOT):
                                    allowed = True
                                else:
                                    allowed = (
                                        unit.code.value == "PCS" and serial_compatible
                                    )
                                if allowed:
                                    item = factory(**values)
                                    self.assertEqual(item.base_uom, unit.code)
                                    self.assertIs(item.quantity_rules, rules)
                                    self.assertIs(item.tracking_mode, tracking)
                                    self.assertIs(item.expiration_mode, expiration)
                                else:
                                    with self.assertRaises(
                                        InvalidTrackingConfigurationError
                                    ):
                                        factory(**values)

    def test_unknown_unit_is_rejected_for_every_tracking_mode(self) -> None:
        """Код неизвестной единицы не становится допустимым в режиме без прослеживаемости."""
        for factory in (self.make_item, self.restore_item):
            for tracking in TrackingMode:
                for code in ("BOX", "kg", "pcs", "UNKNOWN"):
                    with (
                        self.subTest(factory=factory, tracking=tracking, code=code),
                        self.assertRaises(UnknownUomError),
                    ):
                        factory(
                            tracking_mode=tracking,
                            expiration_mode=ExpirationMode.NONE,
                            base_uom=UomCodeVO(code),
                        )

    def test_serial_item_accepts_only_integral_quantities_including_zero(self) -> None:
        """Серийный товар принимает целое количество экземпляров без дробных штук и округления."""
        for tracking in (TrackingMode.SERIAL, TrackingMode.LOT_AND_SERIAL):
            item = self.make_item(
                tracking_mode=tracking, expiration_mode=ExpirationMode.OPTIONAL
            )
            self.assertEqual(
                tuple(unit.code for unit in item.available_uoms), (self.pcs,)
            )
            for value in ("0", "1", "12.000"):
                with self.subTest(tracking=tracking, value=value):
                    quantity = item.to_base_quantity(
                        quantity=QuantityVO(Decimal(value)), uom=self.pcs
                    )
                    self.assertEqual(quantity.value, Decimal(value))
            for value in ("0.5", "1.001"):
                with (
                    self.subTest(tracking=tracking, value=value),
                    self.assertRaises(QuantityStepError),
                ):
                    item.to_base_quantity(
                        quantity=QuantityVO(Decimal(value)), uom=self.pcs
                    )

    def test_factories_require_typed_manual_state(self) -> None:
        """Отклоняет отсутствие SKU, чужие ID, сырые режимы и изменяемые коллекции."""
        for factory in (self.make_item, self.restore_item):
            for changes in (
                {"sku": None},
                {"sku": "MANUAL"},
                {"base_uom": None},
                {"quantity_rules": None},
                {"quantity_rules": {"step": Decimal(1)}},
                {"identifier": self.barcode.id},
                {"tracking_mode": "LOT"},
                {"expiration_mode": "OPTIONAL"},
                {"barcodes": []},
                {"barcodes": (object(),)},
            ):
                with self.subTest(factory=factory, changes=changes):
                    with self.assertRaises(InvalidInventoryItemValueError):
                        factory(**changes)

    def test_factories_reject_duplicate_barcode_ids_and_values(self) -> None:
        """Создание и восстановление сохраняют уникальность ID и кодов штрихкодов."""
        for factory in (self.make_item, self.restore_item):
            for duplicate in (
                replace(self.barcode, barcode=BarcodeVO("456")),
                replace(self.barcode, id=ItemBarcodeIdVO(uuid4())),
            ):
                with self.subTest(factory=factory, duplicate=duplicate):
                    with self.assertRaises(InventoryItemConflictError):
                        factory(barcodes=(self.barcode, duplicate))

    def test_factories_check_child_values_even_if_constructor_was_used_directly(
        self,
    ) -> None:
        """Не позволяет сохранить Entity с сырым значением вместо BarcodeVO."""
        for factory in (self.make_item, self.restore_item):
            with (
                self.subTest(factory=factory),
                self.assertRaises(InvalidInventoryItemValueError),
            ):
                factory(barcodes=(replace(self.barcode, barcode="000123"),))

    def test_barcodes_identify_item_without_any_packaging(self) -> None:
        """Штрихкод принадлежит товару и не задаёт упаковку, количество или единицу."""
        self.assertEqual(
            [field.name for field in fields(ItemBarcode)], ["id", "barcode"]
        )
        self.assertEqual(self.item.packagings, ())
        self.assertEqual(self.restore_item().barcodes, (self.barcode,))

    def test_change_sku_preserves_identity_and_original_state(self) -> None:
        """Меняет ручной SKU только у нового экземпляра с прежним ID и составом."""
        changed = self.item.change_sku(SkuVO(" replacement "))
        self.assertEqual(changed.sku.value, "replacement")
        self.assertEqual(changed.id, self.item.id)
        self.assertEqual(changed.barcodes, self.item.barcodes)
        self.assertEqual(self.item.sku.value, "sku-001")
        with self.assertRaises(InvalidInventoryItemValueError):
            self.item.change_sku(None)
        self.assertEqual(self.item.sku.value, "sku-001")

    def test_barcode_lifecycle_is_controlled_by_the_aggregate(self) -> None:
        """Добавляет, меняет и удаляет штрихкод с сохранением его ID."""
        barcode = ItemBarcode.create(
            identifier=ItemBarcodeIdVO(uuid4()),
            barcode=BarcodeVO("000456"),
        )
        added = self.item.add_barcode(barcode)
        changed = added.change_barcode(
            identifier=barcode.id,
            barcode=BarcodeVO("000789"),
        )
        self.assertEqual(changed.barcodes[-1].id, barcode.id)
        self.assertEqual(changed.barcodes[-1].barcode.value, "000789")
        self.assertEqual(changed.remove_barcode(barcode.id), self.item)
        self.assertEqual(self.item.barcodes, (self.barcode,))

    def test_invalid_barcode_changes_leave_original_composition_intact(self) -> None:
        """Отклоняет дубликаты и неверные значения штрихкода без частичных изменений."""
        other = replace(
            self.barcode, id=ItemBarcodeIdVO(uuid4()), barcode=BarcodeVO("456")
        )
        item = self.item.add_barcode(other)
        for action in (
            lambda: item.add_barcode(other),
            lambda: item.change_barcode(
                identifier=other.id,
                barcode=self.barcode.barcode,
            ),
        ):
            with self.assertRaises(InventoryItemConflictError):
                action()
            self.assertEqual(item.barcodes, (self.barcode, other))
        with self.assertRaises(InvalidInventoryItemValueError):
            item.change_barcode(identifier=other.id, barcode=None)
        self.assertEqual(item.barcodes, (self.barcode, other))

    def test_foreign_children_cannot_be_changed_or_removed(self) -> None:
        """Отклоняет изменение штрихкодов, отсутствующих в этой позиции."""
        barcode_id = ItemBarcodeIdVO(uuid4())
        for action in (
            lambda: self.item.remove_barcode(barcode_id),
            lambda: self.item.change_barcode(
                identifier=barcode_id, barcode=self.barcode.barcode
            ),
        ):
            with self.assertRaises(InventoryItemComponentNotFoundError):
                action()

    def test_aggregate_entities_and_values_are_immutable(self) -> None:
        """Защищает ID, настройки и дочерние данные от прямого присваивания."""
        for obj, name, value in (
            (self.item, "id", InventoryItemIdVO(uuid4())),
            (self.item, "base_uom", UomCodeVO("KG")),
            (self.item, "tracking_mode", TrackingMode.SERIAL),
            (self.item, "expiration_mode", ExpirationMode.NONE),
            (self.item, "barcodes", ()),
            (self.barcode, "barcode", BarcodeVO("CHANGED")),
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
                ),
                self.barcode,
            )
            with self.assertRaises(InvalidInventoryItemValueError):
                factory(
                    identifier=self.identifier,
                    barcode=self.barcode.barcode,
                )
