"""Сохранённый пересчёт исходного количества в базовую единицу записи Ledger."""

import unittest
from dataclasses import FrozenInstanceError
from decimal import (
    Decimal,
    Inexact,
    MAX_EMAX,
    MIN_EMIN,
    ROUND_DOWN,
    Rounded,
    localcontext,
)
from unittest.mock import patch
from uuid import uuid4

from src.modules.inventory.domain.error import (
    IncompatibleUomError,
    InvalidQuantityConversionError,
    QuantityConversionMismatchError,
    UnknownUomError,
)
from src.modules.inventory.domain.stock_position.value_object.identifier import (
    StockPositionIdVO,
)
from src.modules.inventory.domain.stock_posting.entity.stock_ledger_entry import (
    StockLedgerEntry,
)
from src.modules.inventory.domain.stock_posting.error import (
    InvalidStockLedgerEntryError,
    ZeroStockLedgerDeltaError,
)
from src.modules.inventory.domain.stock_posting.value_object.ledger_entry_id import (
    StockLedgerEntryIdVO,
)
from src.modules.inventory.domain.value_object.quantity import QuantityVO
from src.modules.inventory.domain.value_object.quantity_conversion_snapshot import (
    QuantityConversionSnapshotVO,
)
from src.modules.inventory.domain.value_object.stock_delta import StockDeltaVO
from src.modules.inventory.domain.value_object.uom_code import UomCodeVO
from src.modules.shared.domain.domain_error import EntityIdTypeError


class LedgerConversionDomainTests(unittest.TestCase):
    """Проверяет новый системный пересчёт и сохранение исторических величин."""

    def conversion(
        self, quantity: str = "5000", uom: str = "G", base: str = "KG"
    ) -> QuantityConversionSnapshotVO:
        """Фиксирует коэффициент из действующего справочника единиц."""
        return QuantityConversionSnapshotVO.create(
            quantity=QuantityVO(Decimal(quantity)),
            uom=UomCodeVO(uom),
            base_uom=UomCodeVO(base),
        )

    def values(self, **changes: object) -> dict[str, object]:
        """Возвращает типизированный состав записи поступления пяти килограммов."""
        return (
            dict(
                identifier=StockLedgerEntryIdVO(uuid4()),
                position_id=StockPositionIdVO(uuid4()),
                quantity_delta=StockDeltaVO(Decimal(5)),
                base_uom=UomCodeVO("KG"),
                conversion=self.conversion(),
            )
            | changes
        )

    def test_system_conversion_for_all_dimensions(self) -> None:
        """Фиксирует точные коэффициенты количества, массы, объёма, площади и длины."""
        for quantity, uom, base, factor, result in (
            ("5", "PCS", "PCS", "1", "5"),
            ("5000", "G", "KG", "0.001", "5"),
            ("1500", "ML", "L", "0.001", "1.5"),
            ("25000", "CM2", "M2", "0.0001", "2.5"),
            ("250", "CM", "M", "0.01", "2.5"),
            ("1", "T", "G", "1000000", "1000000"),
        ):
            with self.subTest(uom=uom, base=base):
                conversion = self.conversion(quantity, uom, base)
                self.assertEqual(conversion.factor_to_base, Decimal(factor))
                self.assertEqual(conversion.to_base_quantity().value, Decimal(result))
                self.assertEqual(conversion.quantity.value, Decimal(quantity))

    def test_snapshot_rejects_raw_zero_and_invalid_factors(self) -> None:
        """Не допускает нулевого исходного количества, сырых значений и неконечных коэффициентов."""
        values = dict(
            quantity=QuantityVO(Decimal(1)),
            uom=UomCodeVO("KG"),
            factor_to_base=Decimal(1),
        )
        invalid = [
            dict(quantity=QuantityVO(Decimal(0))),
            dict(quantity=Decimal(1)),
            dict(uom="KG"),
        ]
        invalid += [
            dict(factor_to_base=value)
            for value in (
                None,
                1,
                1.0,
                True,
                "1",
                Decimal(0),
                Decimal(-1),
                Decimal("NaN"),
                Decimal("sNaN"),
                Decimal("Infinity"),
                Decimal("-Infinity"),
            )
        ]
        for changes in invalid:
            with (
                self.subTest(changes=changes),
                self.assertRaises(InvalidQuantityConversionError),
            ):
                QuantityConversionSnapshotVO(**(values | changes))
        with self.assertRaises(UnknownUomError):
            QuantityConversionSnapshotVO(
                QuantityVO(Decimal(1)), UomCodeVO("BOX"), Decimal(1)
            )

    def test_incompatible_units_are_rejected(self) -> None:
        """Не превращает килограммы в литры или штуки по произвольному коэффициенту."""
        with self.assertRaises(IncompatibleUomError):
            self.conversion("1", "KG", "L")
        with self.assertRaises(IncompatibleUomError):
            StockLedgerEntry.restore(**self.values(base_uom=UomCodeVO("L")))

    def test_zero_delta_is_forbidden_only_for_ledger(self) -> None:
        """Общий StockDeltaVO допускает ноль, но запись движения его отклоняет."""
        for value in ("0", "-0.000"):
            with (
                self.subTest(value=value),
                self.assertRaises(ZeroStockLedgerDeltaError),
            ):
                StockLedgerEntry.create(
                    **self.values(quantity_delta=StockDeltaVO(Decimal(value)))
                )

    def test_original_quantity_matches_magnitude_for_both_signs(self) -> None:
        """Знак задаётся дельтой, а положительное исходное количество сохраняется неизменным."""
        for value in ("5", "-5", "5.000"):
            entry = StockLedgerEntry.create(
                **self.values(quantity_delta=StockDeltaVO(Decimal(value)))
            )
            self.assertEqual(entry.quantity_delta.value, Decimal(value))
            self.assertEqual(entry.conversion.quantity.value, Decimal(5000))
        for value in ("4.99", "-5.01"):
            with (
                self.subTest(value=value),
                self.assertRaises(QuantityConversionMismatchError),
            ):
                StockLedgerEntry.restore(
                    **self.values(quantity_delta=StockDeltaVO(Decimal(value)))
                )

    def test_restore_preserves_historical_coefficient_without_catalogue_recalculation(
        self,
    ) -> None:
        """Восстановление использует сохранённое равенство, создание сверяет коэффициент со справочником."""
        historical = QuantityConversionSnapshotVO(
            QuantityVO(Decimal(5000)), UomCodeVO("G"), Decimal("0.002")
        )
        values = self.values(
            quantity_delta=StockDeltaVO(Decimal(10)), conversion=historical
        )
        with patch(
            "src.modules.inventory.domain.stock_posting.entity.stock_ledger_entry.UomConversionPolicy.convert",
            side_effect=RuntimeError("Не пересчитывать историю"),
        ):
            restored = StockLedgerEntry.restore(**values)
        self.assertIs(restored.conversion, historical)
        self.assertEqual(restored.quantity_delta.value, Decimal(10))
        with self.assertRaises(QuantityConversionMismatchError):
            StockLedgerEntry.create(**values)

    def test_decimal_context_does_not_round_or_change_flags(self) -> None:
        """Внешняя точность и traps не меняют сохранённый результат пересчёта."""
        with localcontext() as context:
            context.prec = 2
            context.Emax = 2
            context.Emin = -2
            context.rounding = ROUND_DOWN
            context.traps[Inexact] = True
            context.traps[Rounded] = True
            conversion = self.conversion("12345678901234567890.1234500")
            entry = StockLedgerEntry.create(
                **self.values(
                    conversion=conversion,
                    quantity_delta=StockDeltaVO(
                        Decimal("12345678901234567.8901234500")
                    ),
                )
            )
            self.assertEqual(entry.conversion.factor_to_base, Decimal("0.001"))
            self.assertFalse(any(context.flags.values()))

    def test_extreme_products_fail_with_domain_error_instead_of_infinity_or_rounding(
        self,
    ) -> None:
        """Переполнение и потеря младших разрядов не создают недостоверный Ledger."""
        for quantity, factor in (
            (Decimal((0, (9,), MAX_EMAX)), Decimal(10)),
            (Decimal((0, (1,), MIN_EMIN)), Decimal((0, (1,), MIN_EMIN))),
        ):
            conversion = QuantityConversionSnapshotVO(
                QuantityVO(quantity), UomCodeVO("KG"), factor
            )
            with (
                self.subTest(quantity=quantity),
                self.assertRaises(InvalidQuantityConversionError),
            ):
                conversion.to_base_quantity()

    def test_entity_requires_typed_own_state(self) -> None:
        """Восстановление не принимает сырые идентификаторы, единицы, числа или снимки."""
        for changes in (
            dict(identifier=uuid4()),
            dict(position_id=uuid4()),
            dict(quantity_delta=Decimal(5)),
            dict(base_uom="KG"),
            dict(conversion=None),
        ):
            with (
                self.subTest(changes=changes),
                self.assertRaises(InvalidStockLedgerEntryError),
            ):
                StockLedgerEntry.restore(**self.values(**changes))
        with self.assertRaises(EntityIdTypeError):
            StockLedgerEntryIdVO("id")

    def test_entity_restore_preserves_identity_and_values(self) -> None:
        """Явная фабрика восстановления сохраняет полный состав и все ссылки на VO."""
        values = self.values()
        restored = StockLedgerEntry.restore(**values)
        self.assertIs(restored.id, values["identifier"])
        for name in ("position_id", "quantity_delta", "base_uom", "conversion"):
            self.assertIs(getattr(restored, name), values[name])
        with self.assertRaises(FrozenInstanceError):
            restored.quantity_delta = StockDeltaVO(Decimal(3))
        with self.assertRaises(FrozenInstanceError):
            restored.conversion.factor_to_base = Decimal(2)


if __name__ == "__main__":
    unittest.main()
