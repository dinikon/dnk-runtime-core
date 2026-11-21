"""Потребление стоимостного слоя, накопленное округление и восстановление остатков."""

import unittest
from dataclasses import FrozenInstanceError, replace
from datetime import timedelta, timezone
from decimal import Decimal, Inexact, ROUND_DOWN, Rounded, localcontext

from test import test_inventory_valuation_layer_domain as valuation_fixture
from src.modules.inventory.domain.policy.valuation_layer_consumption import (
    ValuationLayerConsumptionPolicy,
)
from src.modules.inventory.domain.valuation_layer.aggregate import ValuationLayer
from src.modules.inventory.domain.valuation_layer.error import (
    InvalidValuationLayerValueError,
    ValuationLayerConsumptionError,
    ValuationLayerTimeError,
    ValuationLayerVersionConflictError,
)
from src.modules.inventory.domain.value_object.quantity import QuantityVO
from src.modules.shared.domain.value_object.currency import CurrencyVO
from src.modules.shared.domain.value_object.money import MoneyVO


class ValuationConsumptionDomainTests(unittest.TestCase):
    """Проверяет остатки стоимости независимо от физических движений и текущих справочников."""

    def setUp(self) -> None:
        """Готовит основание поступления и явный момент изменения слоя."""
        self.f = valuation_fixture.ValuationLayerDomainTests()
        self.f.setUp()
        self.at = self.f.at + timedelta(hours=1)

    def create(self, quantity: str = "3", cost: str = "1") -> ValuationLayer:
        """Фиксирует заданные исходные количество и стоимость по снимку поступления."""
        return self.f.create(
            receipt=replace(self.f.receipt, quantity=QuantityVO(Decimal(quantity))),
            total_cost=MoneyVO(Decimal(cost), CurrencyVO("UAH")),
        )

    def consume(self, layer: ValuationLayer, quantity: str) -> ValuationLayer:
        """Потребляет количество с актуальной версией и явным временем."""
        return layer.consume(
            QuantityVO(Decimal(quantity)),
            expected_version=layer.version,
            updated_at=self.at,
        )

    def malformed_quantity(self, value: object) -> QuantityVO:
        """Создаёт повреждённый сохранённый VO для проверки защиты публичного корня."""
        quantity = object.__new__(QuantityVO)
        object.__setattr__(quantity, "value", value)
        return quantity

    def malformed_money(self, value: object) -> MoneyVO:
        """Создаёт повреждённую сохранённую стоимость без вызова нормализации MoneyVO."""
        money = object.__new__(MoneyVO)
        object.__setattr__(money, "amount", value)
        object.__setattr__(money, "currency", CurrencyVO("UAH"))
        return money

    def test_partial_consumption_updates_only_remaining_state(self) -> None:
        """Расход 30 из 100 за 5000 оставляет 70 за 3500 и одну новую версию."""
        layer = self.create("100", "5000")
        result = self.consume(layer, "30")
        self.assertEqual(result.remaining_qty, QuantityVO(Decimal(70)))
        self.assertEqual(result.remaining_cost.amount, Decimal("3500.0000"))
        self.assertEqual(
            layer.remaining_cost - result.remaining_cost,
            MoneyVO(Decimal(1500), CurrencyVO("UAH")),
        )
        self.assertEqual(result.version, 1)
        self.assertEqual(result.updated_at, self.at)
        for name in (
            "id",
            "source",
            "inventory_item_id",
            "owner_id",
            "warehouse_id",
            "base_uom",
            "cost_basis",
            "received_at",
            "created_at",
        ):
            self.assertEqual(getattr(result, name), getattr(layer, name))

    def test_full_consumption_exhausts_quantity_and_cost(self) -> None:
        """Последний расход обнуляет оба остатка без дополнительной корректировки."""
        result = self.consume(self.create(), "3")
        self.assertTrue(result.is_exhausted())
        self.assertEqual(result.remaining_qty.value, Decimal(0))
        self.assertEqual(result.remaining_cost.amount, Decimal("0.0000"))
        self.assertEqual(result.remaining_cost.currency, CurrencyVO("UAH"))

    def test_cumulative_rounding_distributes_three_consumptions(self) -> None:
        """Для трёх единиц за единицу стоимости расходы равны .3333, .3334, .3333."""
        layer = self.create()
        costs = []
        remains = []
        for _ in range(3):
            next_layer = self.consume(layer, "1")
            costs.append((layer.remaining_cost - next_layer.remaining_cost).amount)
            remains.append(next_layer.remaining_cost.amount)
            layer = next_layer
        self.assertEqual(costs, list(map(Decimal, (".3333", ".3334", ".3333"))))
        self.assertEqual(remains, list(map(Decimal, (".6667", ".3333", "0"))))
        self.assertEqual(layer.version, 3)

    def test_partition_independence_at_same_cumulative_quantity(self) -> None:
        """Разные разбиения одного суммарного расхода дают одинаковую стоимость остатка."""
        layer = self.create("7", "1")
        combined = self.consume(layer, "4.125")
        for parts in (("1", "3.125"), (".125", "2", "2"), ("4", ".125")):
            result = layer
            for part in parts:
                result = self.consume(result, part)
            self.assertEqual(result.remaining_qty, combined.remaining_qty)
            self.assertEqual(result.remaining_cost, combined.remaining_cost)

    def test_zero_remaining_cost_does_not_imply_exhaustion(self) -> None:
        """Округлённый денежный остаток может стать нулём раньше физического количества."""
        layer = self.create("3", ".0001")
        first = self.consume(layer, "1")
        second = self.consume(first, "1")
        self.assertEqual(first.remaining_cost.amount, Decimal(".0001"))
        self.assertEqual(second.remaining_cost.amount, Decimal(0))
        self.assertEqual(second.remaining_qty.value, Decimal(1))
        self.assertFalse(second.is_exhausted())
        self.assertTrue(self.consume(second, "1").is_exhausted())

    def test_half_up_tie_rounds_cumulative_cost_up(self) -> None:
        """Ровно половина денежного кванта относится на накопленный расход."""
        result = self.consume(self.create("2", ".0001"), "1")
        self.assertEqual(result.remaining_cost.amount, Decimal(0))
        self.assertFalse(result.is_exhausted())

    def test_free_receipt_can_be_partially_and_fully_consumed(self) -> None:
        """Бесплатный слой сохраняет нулевую стоимость при положительном остатке количества."""
        layer = self.create("3", "0")
        self.assertFalse(layer.is_exhausted())
        partial = self.consume(layer, "1")
        self.assertEqual(partial.remaining_cost.amount, Decimal(0))
        self.assertFalse(partial.is_exhausted())
        self.assertTrue(self.consume(partial, "2").is_exhausted())

    def test_fractional_quantity_has_exact_remaining_value(self) -> None:
        """Дробный вес потребляется точно без округлённой цены базовой единицы."""
        result = self.consume(self.create(".125", "6.25"), ".03125")
        self.assertEqual(result.remaining_qty.value, Decimal(".09375"))
        self.assertEqual(result.remaining_cost.amount, Decimal("4.6875"))

    def test_success_preserves_immutable_original_and_physical_state(self) -> None:
        """Потребление возвращает другой корень и не меняет Ledger или StockPosition."""
        layer = self.create()
        original = self.f.restore(layer)
        posting = self.f.posting.snapshot()
        balance = self.f.f.first.on_hand_qty
        result = self.consume(layer, "1")
        self.assertIsNot(result, layer)
        self.assertEqual(layer, original)
        self.assertIs(result.cost_basis, layer.cost_basis)
        self.assertIs(result.source, layer.source)
        self.assertEqual(self.f.posting.snapshot(), posting)
        self.assertEqual(self.f.f.first.on_hand_qty, balance)
        with self.assertRaises(FrozenInstanceError):
            result.version = 10

    def test_zero_and_raw_quantities_are_rejected_without_mutation(self) -> None:
        """Корень отклоняет ноль и нетипизированные аргументы расхода."""
        layer = self.create()
        original = self.f.restore(layer)
        for quantity in (QuantityVO(Decimal(0)), Decimal(1), 1, "1", None):
            with (
                self.subTest(quantity=quantity),
                self.assertRaises(ValuationLayerConsumptionError),
            ):
                layer.consume(quantity, expected_version=0, updated_at=self.at)
        self.assertEqual(layer, original)

    def test_corrupted_consumption_quantities_are_rejected(self) -> None:
        """Даже обход конструктора VO не позволяет списать отрицательное или неконечное количество."""
        layer = self.create()
        for value in (
            Decimal(-1),
            Decimal("NaN"),
            Decimal("sNaN"),
            Decimal("Infinity"),
            "1",
        ):
            with (
                self.subTest(value=value),
                self.assertRaises(ValuationLayerConsumptionError),
            ):
                layer.consume(
                    self.malformed_quantity(value),
                    expected_version=0,
                    updated_at=self.at,
                )

    def test_overconsumption_uses_current_remaining_quantity(self) -> None:
        """Ограничение проверяется по текущему остатку после частичного расхода."""
        layer = self.consume(self.create(), "2")
        with self.assertRaises(ValuationLayerConsumptionError):
            self.consume(layer, "2")
        self.assertEqual(layer.remaining_qty.value, Decimal(1))

    def test_exhausted_layer_rejects_another_consumption(self) -> None:
        """Исчерпанный слой не допускает нового положительного расхода."""
        layer = self.consume(self.create(), "3")
        with self.assertRaises(ValuationLayerConsumptionError):
            self.consume(layer, ".0001")

    def test_stale_version_rejects_retry(self) -> None:
        """Повтор со старой версией не потребляет остаток ещё раз."""
        layer = self.consume(self.create(), "1")
        with self.assertRaises(ValuationLayerVersionConflictError):
            layer.consume(
                QuantityVO(Decimal(1)), expected_version=0, updated_at=self.at
            )
        self.assertEqual(layer.remaining_qty.value, Decimal(2))

    def test_new_version_allows_another_consumption_without_fact_deduplication(
        self,
    ) -> None:
        """Актуальная версия означает новый расход; глобальная идемпотентность требует будущего хранения."""
        result = self.consume(self.consume(self.create(), "1"), "1")
        self.assertEqual(result.version, 2)
        self.assertEqual(result.remaining_qty.value, Decimal(1))

    def test_expected_version_requires_strict_nonnegative_integer(self) -> None:
        """Булево значение не считается версией, как и дробь, строка или отрицательное число."""
        layer = self.create()
        for version in (False, True, -1, 0.0, "0", None):
            with (
                self.subTest(version=version),
                self.assertRaises(InvalidValuationLayerValueError),
            ):
                layer.consume(
                    QuantityVO(Decimal(1)), expected_version=version, updated_at=self.at
                )

    def test_consumption_normalizes_aware_time_and_allows_equal_time(self) -> None:
        """Явное смещение нормализуется в UTC; одинаковые моменты последовательных версий допустимы."""
        layer = self.create()
        first = layer.consume(
            QuantityVO(Decimal(1)),
            expected_version=0,
            updated_at=self.at.astimezone(timezone(timedelta(hours=2))),
        )
        self.assertEqual(first.updated_at, self.at)
        self.assertEqual(first.updated_at.utcoffset(), timedelta(0))
        self.assertEqual(self.consume(first, "1").updated_at, self.at)

    def test_consumption_rejects_earlier_time(self) -> None:
        """Время следующего расхода не может предшествовать уже сохранённому изменению."""
        layer = self.consume(self.create(), "1")
        with self.assertRaises(ValuationLayerTimeError):
            layer.consume(
                QuantityVO(Decimal(1)),
                expected_version=1,
                updated_at=self.at - timedelta(microseconds=1),
            )

    def test_consumption_rejects_naive_and_raw_time(self) -> None:
        """Расход не читает часы и требует явный aware datetime."""
        layer = self.create()
        for at in (self.at.replace(tzinfo=None), None, "now"):
            with self.subTest(at=at), self.assertRaises(ValuationLayerTimeError):
                layer.consume(QuantityVO(Decimal(1)), expected_version=0, updated_at=at)

    def test_restore_preserves_partial_and_exhausted_layers(self) -> None:
        """Для восстановления любого остатка достаточно собственных полей без внешнего источника."""
        for layer in (
            self.consume(self.create(), "1"),
            self.consume(self.create(), "3"),
        ):
            self.assertEqual(self.f.restore(layer), layer)
            self.assertEqual(
                self.f.restore(
                    layer,
                    updated_at=layer.updated_at.astimezone(
                        timezone(timedelta(hours=-3))
                    ),
                ),
                layer,
            )

    def test_restore_rejects_remaining_quantity_outside_original_basis(self) -> None:
        """Остаток не превышает первоначальное количество и остаётся конечным типизированным значением."""
        layer = self.create()
        for quantity in (
            QuantityVO(Decimal(4)),
            Decimal(2),
            None,
            self.malformed_quantity(Decimal(-1)),
            self.malformed_quantity(Decimal("NaN")),
        ):
            with (
                self.subTest(quantity=quantity),
                self.assertRaises(InvalidValuationLayerValueError),
            ):
                self.f.restore(layer, remaining_qty=quantity)

    def test_restore_rejects_inconsistent_intermediate_cost(self) -> None:
        """Промежуточная стоимость проверяется по накопленной формуле, а не только по диапазону."""
        layer = self.consume(self.create(), "1")
        for amount in (".6666", ".6668", "1", "0", "-1", "2"):
            with (
                self.subTest(amount=amount),
                self.assertRaises(InvalidValuationLayerValueError),
            ):
                self.f.restore(
                    layer, remaining_cost=MoneyVO(Decimal(amount), CurrencyVO("UAH"))
                )

    def test_restore_rejects_wrong_currency_and_money_type(self) -> None:
        """Остаточная стоимость сохраняет исходную валюту и денежный контракт."""
        layer = self.create()
        for cost in (MoneyVO(Decimal(1), CurrencyVO("EUR")), Decimal(1), None):
            with (
                self.subTest(cost=cost),
                self.assertRaises(InvalidValuationLayerValueError),
            ):
                self.f.restore(layer, remaining_cost=cost)

    def test_restore_rejects_noncanonical_and_nonfinite_money(self) -> None:
        """Повреждённые сохранённые суммы не округляются повторно и не проходят сравнение."""
        for amount in (
            Decimal("1.00001"),
            Decimal("NaN"),
            Decimal("sNaN"),
            Decimal("Infinity"),
            "1",
        ):
            with (
                self.subTest(amount=amount),
                self.assertRaises(InvalidValuationLayerValueError),
            ):
                self.f.restore(
                    self.create(), remaining_cost=self.malformed_money(amount)
                )

    def test_restore_rejects_exhausted_quantity_with_nonzero_cost(self) -> None:
        """Полное количественное исчерпание требует точного денежного нуля."""
        layer = self.create()
        with self.assertRaises(InvalidValuationLayerValueError):
            self.f.restore(layer, remaining_qty=QuantityVO(Decimal(0)))

    def test_restore_rejects_zero_cost_before_cumulative_rounding_allows_it(
        self,
    ) -> None:
        """Нулевую стоимость нельзя произвольно назначить частично потреблённому платному слою."""
        layer = self.create()
        with self.assertRaises(InvalidValuationLayerValueError):
            self.f.restore(layer, remaining_cost=MoneyVO(Decimal(0), CurrencyVO("UAH")))

    def test_restore_requires_strict_nonnegative_version(self) -> None:
        """Версия сохранённого корня проверяется так же строго, как ожидаемая версия команды."""
        for version in (False, True, -1, 1.0, "1", None):
            with (
                self.subTest(version=version),
                self.assertRaises(InvalidValuationLayerValueError),
            ):
                self.f.restore(self.create(), version=version)

    def test_restore_rejects_update_before_creation_or_naive_time(self) -> None:
        """Хронология требует received_at <= created_at <= updated_at с явными часовыми поясами."""
        layer = self.create()
        for at in (
            layer.created_at - timedelta(seconds=1),
            self.at.replace(tzinfo=None),
            None,
        ):
            with self.subTest(at=at), self.assertRaises(ValuationLayerTimeError):
                self.f.restore(layer, updated_at=at)

    def test_consume_revalidates_corrupted_own_state(self) -> None:
        """Прямой обход фабрики не позволяет использовать несогласованный остаток корня."""
        layer = replace(
            self.create(), remaining_cost=MoneyVO(Decimal(0), CurrencyVO("UAH"))
        )
        with self.assertRaises(InvalidValuationLayerValueError):
            self.consume(layer, "1")
        with self.assertRaises(InvalidValuationLayerValueError):
            layer.is_exhausted()

    def test_small_hostile_decimal_context_does_not_affect_rounding(self) -> None:
        """Малая точность, другой режим округления и traps не меняют результат политики или корня."""
        layer = self.create()
        with localcontext() as ctx:
            ctx.prec = 1
            ctx.Emax = 2
            ctx.Emin = -2
            ctx.rounding = ROUND_DOWN
            ctx.traps[Inexact] = True
            ctx.traps[Rounded] = True
            first = self.consume(layer, "1")
            second = self.consume(first, "1")
            restored = self.f.restore(second)
        self.assertEqual(first.remaining_cost.amount, Decimal(".6667"))
        self.assertEqual(restored.remaining_cost.amount, Decimal(".3333"))

    def test_large_values_are_exact_with_small_decimal_context(self) -> None:
        """Предельная денежная сумма и большое количество не теряют разряды при пропорциональном расходе."""
        layer = self.create("1E+60", "999999999999999.9999")
        with localcontext() as ctx:
            ctx.prec = 2
            ctx.traps[Inexact] = True
            ctx.traps[Rounded] = True
            result = self.consume(layer, "1E+59")
        self.assertEqual(result.remaining_qty.value, Decimal("9E+59"))
        self.assertEqual(result.remaining_cost.amount, Decimal("899999999999999.9999"))

    def test_policy_requires_typed_basis_and_valid_remaining_quantity(self) -> None:
        """Чистая политика проверяет собственный контракт без чтения агрегата и внешних данных."""
        layer = self.create()
        for basis, quantity in (
            (None, layer.remaining_qty),
            (layer.cost_basis, Decimal(1)),
            (layer.cost_basis, QuantityVO(Decimal(4))),
        ):
            with (
                self.subTest(basis=basis, quantity=quantity),
                self.assertRaises(InvalidValuationLayerValueError),
            ):
                ValuationLayerConsumptionPolicy.calculate_remaining_cost(
                    cost_basis=basis, remaining_qty=quantity
                )


if __name__ == "__main__":
    unittest.main()
