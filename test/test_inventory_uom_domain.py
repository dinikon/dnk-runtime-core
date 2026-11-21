"""Общие единицы, точный пересчёт и применение размерностей в InventoryItem."""

import unittest
from dataclasses import FrozenInstanceError, fields
from decimal import Decimal, Inexact, MAX_EMAX, ROUND_DOWN, Rounded, localcontext
from uuid import uuid4

from src.modules.inventory.domain.error import (
    IncompatibleUomError,
    InvalidQuantityError,
    InvalidUomCodeError,
    InvalidUomDefinitionError,
    UnknownUomError,
    UomConversionError,
)
from src.modules.inventory.domain.inventory_item.aggregate import InventoryItem
from src.modules.inventory.domain.inventory_item.value_object.identifier import (
    InventoryItemIdVO,
)
from src.modules.inventory.domain.inventory_item.value_object.sku import SkuVO
from src.modules.inventory.domain.policy.uom_conversion import UomConversionPolicy
from src.modules.inventory.domain.uom_catalog import (
    get_compatible_uoms,
    get_uom,
    list_uoms,
)
from src.modules.inventory.domain.value_object.quantity import QuantityVO
from src.modules.inventory.domain.value_object.quantity_rules import QuantityRulesVO
from src.modules.inventory.domain.value_object.uom_code import UomCodeVO
from src.modules.inventory.domain.value_object.uom_definition import UomDefinitionVO
from src.modules.inventory.domain.value_object.uom_dimension import UomDimension


class UomCatalogTests(unittest.TestCase):
    """Проверяет системные определения без товарных или tenant-настроек множителя."""

    def test_mass_family_is_automatically_available_for_any_mass_unit(self) -> None:
        """Выбор килограмма или грамма открывает одну и ту же полную размерность."""
        expected = {"UG", "MG", "G", "KG", "CENTNER", "T"}
        for code in expected:
            with self.subTest(code=code):
                units = get_compatible_uoms(UomCodeVO(code))
                self.assertEqual({unit.code.value for unit in units}, expected)
                self.assertTrue(
                    all(unit.dimension is UomDimension.MASS for unit in units)
                )

    def test_other_dimensions_have_their_own_system_units(self) -> None:
        """Разделяет объём, длину, площадь и количество, включая микрометр длины."""
        for base, expected in (
            ("L", {"ML", "L", "M3"}),
            ("M", {"UM", "MM", "CM", "DM", "M", "KM"}),
            ("M2", {"MM2", "CM2", "DM2", "M2", "HA", "KM2"}),
            ("PCS", {"PCS"}),
        ):
            with self.subTest(base=base):
                self.assertEqual(
                    {unit.code.value for unit in get_compatible_uoms(UomCodeVO(base))},
                    expected,
                )
        self.assertIs(get_uom(UomCodeVO("UM")).dimension, UomDimension.LENGTH)
        self.assertIs(get_uom(UomCodeVO("UG")).dimension, UomDimension.MASS)

    def test_catalog_and_definitions_are_immutable(self) -> None:
        """Получение справочника не позволяет переписать общий коэффициент."""
        units = list_uoms()
        self.assertIsInstance(units, tuple)
        self.assertEqual(len({unit.code for unit in units}), len(units))
        unit = get_uom(UomCodeVO("KG"))
        self.assertEqual(unit.factor_to_reference, Decimal(1))
        with self.assertRaises(FrozenInstanceError):
            unit.factor_to_reference = Decimal(5)
        custom = UomDefinitionVO(UomCodeVO("CUSTOM"), UomDimension.MASS, Decimal(1))
        with self.assertRaises(UnknownUomError):
            get_uom(custom.code)

    def test_unknown_or_untyped_codes_are_rejected(self) -> None:
        """Справочник принимает точные системные коды, упаковка не является единицей."""
        for lookup in (get_uom, get_compatible_uoms):
            for code in ("UNKNOWN", "kg", "BOX"):
                with (
                    self.subTest(lookup=lookup, code=code),
                    self.assertRaises(UnknownUomError),
                ):
                    lookup(UomCodeVO(code))
            with self.assertRaises(InvalidUomCodeError):
                lookup("KG")

    def test_definition_rejects_invalid_dimension_and_scale(self) -> None:
        """VO проверяет собственные значения без влияния на глобальный справочник."""
        for dimension, factor in (
            ("MASS", Decimal(1)),
            (UomDimension.MASS, Decimal(0)),
            (UomDimension.MASS, Decimal(-1)),
            (UomDimension.MASS, Decimal("NaN")),
            (UomDimension.MASS, Decimal("Infinity")),
            (UomDimension.MASS, 1.0),
        ):
            with (
                self.subTest(dimension=dimension, factor=factor),
                self.assertRaises(InvalidUomDefinitionError),
            ):
                UomDefinitionVO(UomCodeVO("KG"), dimension, factor)


class UomConversionTests(unittest.TestCase):
    """Проверяет точные физические соотношения и независимость арифметического контекста."""

    def convert(self, value: str, source: str, target: str) -> QuantityVO:
        """Пересчитывает явно заданное Decimal-количество между системными кодами."""
        return UomConversionPolicy.convert(
            quantity=QuantityVO(Decimal(value)),
            from_uom=UomCodeVO(source),
            to_uom=UomCodeVO(target),
        )

    def test_known_physical_conversions(self) -> None:
        """Проверяет массу, объём, длину, площадь и тождественный пересчёт штук."""
        for value, source, target, expected in (
            ("2500", "G", "KG", "2.5"),
            ("1", "KG", "UG", "1000000000"),
            ("1", "T", "CENTNER", "10"),
            ("1", "CENTNER", "KG", "100"),
            ("1500", "ML", "L", "1.5"),
            ("1", "M3", "L", "1000"),
            ("350", "CM", "M", "3.5"),
            ("1", "M", "UM", "1000000"),
            ("50000", "CM2", "M2", "5"),
            ("1", "HA", "M2", "10000"),
            ("1", "KM2", "HA", "100"),
            ("24", "PCS", "PCS", "24"),
        ):
            with self.subTest(value=value, source=source, target=target):
                self.assertEqual(
                    self.convert(value, source, target).value, Decimal(expected)
                )

    def test_all_compatible_pairs_round_trip_without_quantity_loss(self) -> None:
        """Каждая пара единиц размерности сохраняет точное количество при обратном переводе."""
        for source in list_uoms():
            for target in get_compatible_uoms(source.code):
                for value in ("0", "1", "123.4500", "0.000000000123456789"):
                    with self.subTest(
                        source=source.code, target=target.code, value=value
                    ):
                        quantity = self.convert(
                            value, source.code.value, target.code.value
                        )
                        restored = UomConversionPolicy.convert(
                            quantity=quantity, from_uom=target.code, to_uom=source.code
                        )
                        self.assertEqual(restored.value, Decimal(value))

    def test_external_decimal_precision_rounding_and_traps_do_not_change_result(
        self,
    ) -> None:
        """Низкая точность и строгие traps вызывающего кода не округляют складское количество."""
        with localcontext() as context:
            context.prec = 2
            context.rounding = ROUND_DOWN
            context.Emax = 2
            context.Emin = -2
            context.traps[Inexact] = True
            context.traps[Rounded] = True
            result = self.convert("12345678901234567890.123456789", "KG", "G")
            self.assertEqual(result.value, Decimal("12345678901234567890123.456789"))
            self.assertEqual(context.prec, 2)

    def test_cross_dimension_conversions_are_rejected(self) -> None:
        """Плотность, ширина и содержимое упаковки не выводятся из системного множителя."""
        for source, target in (("KG", "L"), ("M", "M2"), ("PCS", "KG"), ("UM", "UG")):
            with (
                self.subTest(source=source, target=target),
                self.assertRaises(IncompatibleUomError),
            ):
                self.convert("1", source, target)

    def test_representable_result_does_not_fail_from_intermediate_overflow(
        self,
    ) -> None:
        """Отношение масштабов вычисляется до умножения большого количества."""
        quantity = QuantityVO(Decimal((0, (1,), MAX_EMAX)))
        result = UomConversionPolicy.convert(
            quantity=quantity, from_uom=UomCodeVO("HA"), to_uom=UomCodeVO("KM2")
        )
        self.assertEqual(result.value, Decimal((0, (1,), MAX_EMAX - 2)))

    def test_invalid_quantities_unknown_units_and_overflow_are_domain_errors(
        self,
    ) -> None:
        """Не допускает float, нечисловые значения и тихое получение Infinity."""
        for value in (
            None,
            1,
            1.5,
            "1",
            Decimal(-1),
            Decimal("NaN"),
            Decimal("sNaN"),
            Decimal("Infinity"),
        ):
            with self.subTest(value=value), self.assertRaises(InvalidQuantityError):
                QuantityVO(value)
        with self.assertRaises(InvalidQuantityError):
            UomConversionPolicy.convert(
                quantity=Decimal(1), from_uom=UomCodeVO("KG"), to_uom=UomCodeVO("G")
            )
        with self.assertRaises(UnknownUomError):
            self.convert("1", "UNKNOWN", "KG")
        with self.assertRaises(UomConversionError):
            UomConversionPolicy.convert(
                quantity=QuantityVO(Decimal((0, (1,), MAX_EMAX))),
                from_uom=UomCodeVO("KG"),
                to_uom=UomCodeVO("UG"),
            )

    def test_zero_and_fractional_quantity_have_no_implicit_step_or_rounding(
        self,
    ) -> None:
        """Шаг количества остаётся отдельным будущим правилом товара."""
        self.assertEqual(self.convert("0", "L", "ML").value, Decimal(0))
        self.assertEqual(self.convert("1.5", "PCS", "PCS").value, Decimal("1.5"))


class InventoryItemUomTests(unittest.TestCase):
    """Проверяет интеграцию общих единиц с агрегатом без пользовательских коэффициентов."""

    def make_item(self, base: str) -> InventoryItem:
        """Создаёт товар с выбранной системной базовой единицей."""
        return InventoryItem.create(
            identifier=InventoryItemIdVO(uuid4()),
            sku=SkuVO("ITEM"),
            base_uom=UomCodeVO(base),
            quantity_rules=QuantityRulesVO(Decimal("0.001")),
        )

    def test_item_derives_units_and_converts_to_its_selected_base(self) -> None:
        """Выбор базовой единицы автоматически определяет доступные единицы и расчёт."""
        item = self.make_item("KG")
        other = self.make_item("KG")
        self.assertEqual(item.available_uoms, other.available_uoms)
        self.assertNotIn(
            "uom_conversions", {field.name for field in fields(InventoryItem)}
        )
        self.assertEqual(
            item.to_base_quantity(
                quantity=QuantityVO(Decimal(2500)), uom=UomCodeVO("G")
            ).value,
            Decimal("2.5"),
        )
        grams = self.make_item("G")
        self.assertEqual(
            grams.to_base_quantity(
                quantity=QuantityVO(Decimal("2.5")), uom=UomCodeVO("KG")
            ).value,
            Decimal(2500),
        )
        with self.assertRaises(IncompatibleUomError):
            item.to_base_quantity(quantity=QuantityVO(Decimal(1)), uom=UomCodeVO("L"))

    def test_create_and_restore_reject_unknown_base_units(self) -> None:
        """Не позволяет хранить товар с неопределённой базовой единицей."""
        valid = self.make_item("PCS")
        for code in ("UNKNOWN", "BOX", "kg"):
            with self.subTest(code=code):
                with self.assertRaises(UnknownUomError):
                    self.make_item(code)
                with self.assertRaises(UnknownUomError):
                    InventoryItem.restore(
                        identifier=InventoryItemIdVO(uuid4()),
                        sku=SkuVO("ITEM"),
                        base_uom=UomCodeVO(code),
                        quantity_rules=valid.quantity_rules,
                        tracking_mode=valid.tracking_mode,
                        expiration_mode=valid.expiration_mode,
                        packagings=(),
                        barcodes=(),
                    )
