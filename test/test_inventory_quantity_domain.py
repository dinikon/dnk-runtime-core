"""Правила количества и их применение к товару и содержимому упаковок."""

import unittest
from dataclasses import FrozenInstanceError
from decimal import Decimal, Inexact, MAX_EMAX, ROUND_DOWN, Rounded, localcontext
from fractions import Fraction
from uuid import uuid4

from src.modules.inventory.domain.error import (
    InvalidQuantityError,
    InvalidQuantityRulesError,
    QuantityStepError,
)
from src.modules.inventory.domain.inventory_item.aggregate import InventoryItem
from src.modules.inventory.domain.inventory_item.entity.item_packaging import (
    ItemPackaging,
)
from src.modules.inventory.domain.inventory_item.value_object.identifier import (
    InventoryItemIdVO,
)
from src.modules.inventory.domain.inventory_item.value_object.item_packaging_id import (
    ItemPackagingIdVO,
)
from src.modules.inventory.domain.inventory_item.value_object.packaging_quantity import (
    PackagingQuantityVO,
)
from src.modules.inventory.domain.inventory_item.value_object.sku import SkuVO
from src.modules.inventory.domain.packaging_type.aggregate import PackagingType
from src.modules.inventory.domain.packaging_type.value_object.identifier import (
    PackagingTypeIdVO,
)
from src.modules.inventory.domain.policy.quantity_validation import (
    QuantityValidationPolicy,
)
from src.modules.inventory.domain.value_object.packaging_code import PackagingCodeVO
from src.modules.inventory.domain.value_object.packaging_name import PackagingNameVO
from src.modules.inventory.domain.value_object.quantity import QuantityVO
from src.modules.inventory.domain.value_object.quantity_rules import QuantityRulesVO
from src.modules.inventory.domain.value_object.uom_code import UomCodeVO


class QuantityRulesTests(unittest.TestCase):
    """Проверяет собственные значения неизменяемых правил количества."""

    def test_step_accepts_whole_fractional_and_microgram_values(self) -> None:
        """Шаг определяет допустимую дробность, включая микрограммы в килограммах."""
        for step in ("1.000", "0.0500", "2.5", "1E-9"):
            with self.subTest(step=step):
                rules = QuantityRulesVO(Decimal(step))
                self.assertEqual(rules.step, Decimal(step))

    def test_invalid_types_nonfinite_and_nonpositive_steps_are_rejected(
        self,
    ) -> None:
        """Не принимает float, bool, нулевой, отрицательный и нечисловой шаг."""
        for step in (
            None,
            1,
            0.1,
            True,
            False,
            "1",
            Decimal(0),
            Decimal(-1),
            Decimal("NaN"),
            Decimal("sNaN"),
            Decimal("Infinity"),
        ):
            with self.subTest(step=step), self.assertRaises(InvalidQuantityRulesError):
                QuantityRulesVO(step)

    def test_rules_are_immutable_values(self) -> None:
        """Эквивалентные Decimal-шаги равны, а настройки нельзя изменить на месте."""
        rules = QuantityRulesVO(Decimal("1.00"))
        self.assertEqual(rules, QuantityRulesVO(Decimal(1)))
        self.assertEqual(len({rules, QuantityRulesVO(Decimal(1))}), 1)
        with self.assertRaises(FrozenInstanceError):
            rules.step = Decimal(2)


class QuantityValidationTests(unittest.TestCase):
    """Проверяет точную кратность без округления и внешнего Decimal-контекста."""

    def test_step_defines_allowed_quantities_ignoring_trailing_zeros(self) -> None:
        """Принимает точные кратные независимо от записи и отклоняет любые остальные."""
        rules = QuantityRulesVO(Decimal("0.05"))
        for value in ("0", "-0.00000", "1.2500", "0.05", "10", "1E+30"):
            with self.subTest(value=value):
                self.assertIsNone(
                    QuantityValidationPolicy.validate(
                        quantity=QuantityVO(Decimal(value)), rules=rules
                    )
                )
        for value in ("1.251", "1.23", "0.001"):
            with self.subTest(value=value), self.assertRaises(QuantityStepError):
                QuantityValidationPolicy.validate(
                    quantity=QuantityVO(Decimal(value)), rules=rules
                )

    def test_typed_inputs_are_required(self) -> None:
        """Policy не преобразует сырые числа или словари в доменные значения."""
        with self.assertRaises(InvalidQuantityError):
            QuantityValidationPolicy.validate(
                quantity=Decimal(1), rules=QuantityRulesVO(Decimal(1))
            )
        with self.assertRaises(InvalidQuantityRulesError):
            QuantityValidationPolicy.validate(
                quantity=QuantityVO(Decimal(1)), rules=None
            )

    def test_validation_matches_exact_rational_arithmetic(self) -> None:
        """Сверяет разные шаги с независимым рациональным расчётом, включая целые шаги."""
        values = tuple(Decimal(value).scaleb(-2) for value in range(130)) + tuple(
            Decimal(value)
            for value in (
                "2.5",
                "3",
                "5.0",
                "7.5",
                "10",
                "12.50",
                "30",
                "1000",
                "0.001",
                "1E-9",
            )
        )
        for step in ("0.05", "0.125", "0.2", "2.5", "3", "10"):
            rules = QuantityRulesVO(Decimal(step))
            for value in values:
                fraction = Fraction(value)
                with self.subTest(step=step, value=value):
                    if (fraction / Fraction(rules.step)).denominator != 1:
                        with self.assertRaises(QuantityStepError):
                            QuantityValidationPolicy.validate(
                                quantity=QuantityVO(value), rules=rules
                            )
                    else:
                        QuantityValidationPolicy.validate(
                            quantity=QuantityVO(value), rules=rules
                        )

    def test_external_context_does_not_affect_rules_or_validation(self) -> None:
        """Строгие traps, малая точность и границы порядка не меняют ответ."""
        with localcontext() as context:
            context.prec = 2
            context.Emax = 2
            context.Emin = -2
            context.rounding = ROUND_DOWN
            context.traps[Inexact] = True
            context.traps[Rounded] = True
            rules = QuantityRulesVO(Decimal("0.0500"))
            QuantityValidationPolicy.validate(
                quantity=QuantityVO(Decimal("12345678901234567890.2500")), rules=rules
            )
            with self.assertRaises(QuantityStepError):
                QuantityValidationPolicy.validate(
                    quantity=QuantityVO(Decimal("12345678901234567890.23")), rules=rules
                )
            with self.assertRaises(QuantityStepError):
                QuantityValidationPolicy.validate(
                    quantity=QuantityVO(Decimal("1.251")), rules=rules
                )
            self.assertFalse(any(context.flags.values()))

    def test_extreme_exponents_do_not_require_expanding_decimal_powers(self) -> None:
        """Проверяет огромные порядки без построения целого числа из миллиардов цифр."""
        huge = QuantityVO(Decimal((0, (1,), MAX_EMAX)))
        QuantityValidationPolicy.validate(
            quantity=huge, rules=QuantityRulesVO(Decimal(2))
        )
        with self.assertRaises(QuantityStepError):
            QuantityValidationPolicy.validate(
                quantity=huge, rules=QuantityRulesVO(Decimal(3))
            )
        tiny = QuantityVO(Decimal((0, (1,), -MAX_EMAX)))
        QuantityValidationPolicy.validate(
            quantity=tiny, rules=QuantityRulesVO(tiny.value)
        )
        with self.assertRaises(QuantityStepError):
            QuantityValidationPolicy.validate(
                quantity=tiny, rules=QuantityRulesVO(Decimal(1))
            )


class InventoryItemQuantityTests(unittest.TestCase):
    """Проверяет инварианты количества через публичные фабрики и методы агрегата."""

    def make_item(self, base: str, step: str) -> InventoryItem:
        """Создаёт позицию с явно выбранными правилами базового количества."""
        return InventoryItem.create(
            identifier=InventoryItemIdVO(uuid4()),
            sku=SkuVO("ITEM"),
            base_uom=UomCodeVO(base),
            quantity_rules=QuantityRulesVO(Decimal(step)),
        )

    def restore_item(
        self, item: InventoryItem, packagings: tuple[ItemPackaging, ...]
    ) -> InventoryItem:
        """Восстанавливает полный состав с сохранением правил и идентификаторов."""
        return InventoryItem.restore(
            identifier=item.id,
            sku=item.sku,
            base_uom=item.base_uom,
            quantity_rules=item.quantity_rules,
            tracking_mode=item.tracking_mode,
            expiration_mode=item.expiration_mode,
            packagings=packagings,
            barcodes=item.barcodes,
        )

    def test_rules_apply_after_conversion_for_every_accounting_dimension(self) -> None:
        """Правила относятся к базовой единице, а не к числу знаков исходного ввода."""
        for base, step, source, value, expected in (
            ("PCS", "1", "PCS", "12.000", "12"),
            ("L", "0.001", "ML", "1", "0.001"),
            ("KG", "0.001", "G", "1250", "1.25"),
            ("KG", "0.001", "G", "1", "0.001"),
            ("M2", "0.01", "CM2", "100", "0.01"),
            ("M", "0.1", "CM", "10", "0.1"),
            ("G", "1", "KG", "0.001", "1"),
            ("KG", "0.000000001", "UG", "1", "0.000000001"),
        ):
            with self.subTest(base=base, source=source, value=value):
                item = self.make_item(base, step)
                result = item.to_base_quantity(
                    quantity=QuantityVO(Decimal(value)), uom=UomCodeVO(source)
                )
                self.assertEqual(result.value, Decimal(expected))
                self.assertIs(
                    self.restore_item(item, ()).quantity_rules, item.quantity_rules
                )
                self.assertEqual(
                    item.to_base_quantity(
                        quantity=QuantityVO(Decimal(0)), uom=UomCodeVO(source)
                    ).value,
                    Decimal(0),
                )

    def test_unrepresentable_converted_quantity_is_rejected_without_rounding(
        self,
    ) -> None:
        """Отклоняет дробную штуку, слишком малую массу и некратный шаг после пересчёта."""
        for base, step, source, value in (
            ("PCS", "1", "PCS", "0.5"),
            ("KG", "0.001", "MG", "1"),
            ("KG", "0.05", "G", "30"),
        ):
            with (
                self.subTest(base=base, value=value),
                self.assertRaises(QuantityStepError),
            ):
                self.make_item(base, step).to_base_quantity(
                    quantity=QuantityVO(Decimal(value)), uom=UomCodeVO(source)
                )

    def test_packaging_add_change_and_restore_validate_converted_content(self) -> None:
        """Все пути записи проверяют правила товара, а отказ сохраняет исходный состав."""
        kind = PackagingType.create(
            identifier=PackagingTypeIdVO(uuid4()),
            code=PackagingCodeVO("BAG"),
            name=PackagingNameVO("Мешок"),
        )
        item = self.make_item("KG", "0.05")
        valid = ItemPackaging.create(
            identifier=ItemPackagingIdVO(uuid4()),
            packaging_type_id=kind.id,
            code=PackagingCodeVO("BAG_1250"),
            name=PackagingNameVO("Мешок 1250 г"),
            content_quantity=PackagingQuantityVO(Decimal(1250)),
            content_uom=UomCodeVO("G"),
        )
        with_packaging = item.add_packaging(valid, packaging_type=kind.snapshot())
        self.assertEqual(self.restore_item(with_packaging, (valid,)), with_packaging)
        for value in ("30", "1"):
            invalid = ItemPackaging.create(
                identifier=valid.id,
                packaging_type_id=kind.id,
                code=valid.code,
                name=valid.name,
                content_quantity=PackagingQuantityVO(Decimal(value)),
                content_uom=valid.content_uom,
            )
            with self.subTest(value=value):
                with self.assertRaises(QuantityStepError):
                    item.add_packaging(invalid, packaging_type=kind.snapshot())
                with self.assertRaises(QuantityStepError):
                    self.restore_item(item, (invalid,))
                with self.assertRaises(QuantityStepError):
                    with_packaging.change_packaging(
                        identifier=valid.id,
                        packaging_type=kind.snapshot(),
                        code=valid.code,
                        name=valid.name,
                        content_quantity=invalid.content_quantity,
                        content_uom=valid.content_uom,
                    )
                self.assertEqual(item.packagings, ())
                self.assertEqual(with_packaging.packagings, (valid,))
        changed = with_packaging.change_packaging(
            identifier=valid.id,
            packaging_type=kind.snapshot(),
            code=valid.code,
            name=valid.name,
            content_quantity=PackagingQuantityVO(Decimal(1500)),
            content_uom=valid.content_uom,
        )
        self.assertEqual(changed.packagings[0].content_quantity.value, Decimal(1500))
        self.assertEqual(with_packaging.packagings, (valid,))
        with self.assertRaises(FrozenInstanceError):
            item.quantity_rules = QuantityRulesVO(Decimal(1))
