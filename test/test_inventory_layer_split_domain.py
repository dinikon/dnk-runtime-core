"""Ручное распределение одной записи ISSUE между слоями без автоматического FIFO."""

import unittest
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal, Inexact, Rounded, localcontext
from uuid import UUID, uuid4

from test import test_inventory_issue_valuation_posting_domain as posting_fixture
from src.modules.inventory.domain.error import InventoryError
from src.modules.inventory.domain.inventory_item.value_object.identifier import (
    InventoryItemIdVO,
)
from src.modules.inventory.domain.stock_position.aggregate import StockPosition
from src.modules.inventory.domain.stock_position.value_object.identifier import (
    StockPositionIdVO,
)
from src.modules.inventory.domain.stock_posting.aggregate import StockPosting
from src.modules.inventory.domain.stock_posting.issue_valuation_snapshot import (
    StockIssueValuationSnapshot,
)
from src.modules.inventory.domain.stock_posting.value_object.ledger_entry_id import (
    StockLedgerEntryIdVO,
)
from src.modules.inventory.domain.stock_posting.value_object.operation_type import (
    StockOperationType,
)
from src.modules.inventory.domain.stock_serial.value_object.identifier import (
    StockSerialIdVO,
)
from src.modules.inventory.domain.valuation_layer.aggregate import ValuationLayer
from src.modules.inventory.domain.valuation_layer.consumption_snapshot import (
    ValuationLayerConsumptionSnapshot,
)
from src.modules.inventory.domain.valuation_layer.error import (
    InvalidValuationLayerConsumptionSnapshotError,
    ValuationLayerConsumptionError,
    ValuationLayerVersionConflictError,
)
from src.modules.inventory.domain.valuation_layer.value_object.identifier import (
    ValuationLayerIdVO,
)
from src.modules.inventory.domain.valuation_posting.aggregate import ValuationPosting
from src.modules.inventory.domain.valuation_posting.error import (
    DuplicateValuationEntryError,
    ValuationPostingSourceError,
)
from src.modules.inventory.domain.valuation_posting.value_object.entry_binding import (
    ValuationEntryBindingVO,
)
from src.modules.inventory.domain.valuation_posting.value_object.entry_id import (
    ValuationEntryIdVO,
)
from src.modules.inventory.domain.value_object.quantity import QuantityVO
from src.modules.inventory.domain.value_object.stock_delta import StockDeltaVO
from src.modules.inventory.domain.value_object.stock_owner_id import StockOwnerIdVO
from src.modules.inventory.domain.value_object.uom_code import UomCodeVO
from src.modules.inventory.domain.warehouse.value_object.identifier import WarehouseIdVO
from src.modules.shared.domain.value_object.currency import CurrencyVO
from src.modules.shared.domain.value_object.money import MoneyVO


class LayerSplitDomainTests(unittest.TestCase):
    """Проверяет части потребления, согласованность групп Ledger, точность и неделимость SERIAL."""

    def setUp(self) -> None:
        """Готовит ISSUE семи KG и два поступления одной позиции: три KG за 30 и десять за 120."""
        self.base = posting_fixture.IssueValuationPostingDomainTests()
        self.base.setUp()
        self.fx = self.base.fx
        self.f = self.fx.f
        self.stock = self.fx.issue_for("7")
        self.issue = self.fx.produce(self.stock)
        self.a = self.layer("3", "30", 100)
        self.b = self.layer("10", "120", 200)
        self.after_a, self.part_a = self.a.consume_from_issue(
            self.issue,
            quantity=QuantityVO(Decimal(3)),
            expected_version=0,
            updated_at=self.fx.at,
        )
        self.after_b, self.part_b = self.b.consume_from_issue(
            self.issue,
            quantity=QuantityVO(Decimal(4)),
            expected_version=0,
            updated_at=self.fx.at,
        )
        self.bindings = (
            ValuationEntryBindingVO(self.a.id, ValuationEntryIdVO(uuid4())),
            ValuationEntryBindingVO(self.b.id, ValuationEntryIdVO(uuid4())),
        )

    def layer(
        self, quantity: str, cost: str, index: int, currency: str = "UAH"
    ) -> ValuationLayer:
        """Создаёт реальное поступление исходной позиции и фиксирует его стоимость с явным ID слоя."""
        receipt = self.f.posting(entries=(self.f.entry(quantity),))
        return self.fx.v.create(
            identifier=ValuationLayerIdVO(UUID(int=index)),
            receipt=self.fx.v.produce(receipt),
            total_cost=MoneyVO(Decimal(cost), CurrencyVO(currency)),
        )

    def parts(self, a: str, b: str) -> tuple[ValuationLayerConsumptionSnapshot, ...]:
        """Потребляет явно выбранные количества из двух исходных слоёв без изменения оригиналов."""
        return tuple(
            layer.consume_from_issue(
                self.issue,
                quantity=QuantityVO(Decimal(quantity)),
                expected_version=0,
                updated_at=self.fx.at,
            )[1]
            for layer, quantity in ((self.a, a), (self.b, b))
        )

    def create(self, **changes: object) -> ValuationPosting:
        """Передаёт полный набор частей и прежние привязки в расходный журнал."""
        return self.base.create(
            **(
                dict(
                    posting=self.stock.snapshot(),
                    consumptions=(self.part_a, self.part_b),
                    entry_bindings=self.bindings,
                )
                | changes
            )
        )

    def serial_context(
        self,
    ) -> tuple[
        ValuationLayer, StockPosition, StockPosting, StockIssueValuationSnapshot
    ]:
        """Создаёт поступление и расход одного реального серийного экземпляра в PCS."""
        position = self.f.position(
            dimensions=replace(self.f.dimensions, serial_id=StockSerialIdVO(uuid4())),
            base_uom=UomCodeVO("PCS"),
        )
        receipt = self.f.posting(
            entries=(self.f.entry("1", position),), positions=(position.snapshot(),)
        )
        layer = self.fx.v.create(
            receipt=self.fx.v.produce(receipt, position=position.snapshot()),
            total_cost=MoneyVO(Decimal(10), CurrencyVO("UAH")),
        )
        stock = self.fx.issue_for("1", position)
        return (
            layer,
            position,
            stock,
            self.fx.produce(stock, position=position.snapshot()),
        )

    def test_partial_results_preserve_full_issue_and_selected_quantities(self) -> None:
        """Части три и четыре KG ссылаются на полные семь KG и оцениваются по своим слоям."""
        self.assertEqual(self.part_a.issue.quantity.value, Decimal(7))
        self.assertEqual(self.part_b.issue.quantity.value, Decimal(7))
        self.assertEqual(
            (self.part_a.quantity.value, self.part_b.quantity.value),
            (Decimal(3), Decimal(4)),
        )
        self.assertEqual(
            (self.part_a.cost.amount, self.part_b.cost.amount),
            (Decimal(30), Decimal(48)),
        )
        self.assertTrue(self.after_a.is_exhausted())
        self.assertEqual(self.after_b.remaining_qty.value, Decimal(6))
        self.assertEqual(self.after_b.remaining_cost.amount, Decimal(72))
        self.part_a.ensure_valid()
        self.part_b.ensure_valid()

    def test_journal_creates_two_entries_for_one_ledger_and_position(self) -> None:
        """Одна физическая запись становится двумя записями стоимости разных слоёв."""
        posting = self.create()
        a, b = posting.entries
        self.assertEqual(a.ledger_entry_id, b.ledger_entry_id)
        self.assertEqual(a.position_id, b.position_id)
        self.assertEqual((a.layer_id, b.layer_id), (self.a.id, self.b.id))
        self.assertEqual(
            (a.quantity_delta.value, b.quantity_delta.value), (Decimal(-3), Decimal(-4))
        )
        self.assertEqual(
            (a.cost_delta.amount, b.cost_delta.amount), (Decimal(-30), Decimal(-48))
        )

    def test_omitted_quantity_preserves_full_consumption_api(self) -> None:
        """Старый вызов без quantity по-прежнему потребляет весь ISSUE одним достаточным слоем."""
        after, result = self.b.consume_from_issue(
            self.issue, expected_version=0, updated_at=self.fx.at
        )
        self.assertEqual(result.quantity, self.issue.quantity)
        self.assertEqual(after.remaining_qty.value, Decimal(3))
        posting = self.create(
            consumptions=(result,), entry_bindings=(self.bindings[1],)
        )
        self.assertEqual(posting.entries[0].quantity_delta.value, Decimal(-7))

    def test_explicit_quantity_must_be_positive_finite_nominal_and_within_issue(
        self,
    ) -> None:
        """Часть не может быть нулевой, неконечной, сырой или больше полного ISSUE даже при достаточном слое."""
        for quantity in (
            QuantityVO(Decimal(0)),
            QuantityVO(Decimal(8)),
            Decimal(1),
            self.fx.malformed_quantity(Decimal(-1)),
            self.fx.malformed_quantity(Decimal("NaN")),
        ):
            with (
                self.subTest(quantity=quantity),
                self.assertRaises(ValuationLayerConsumptionError),
            ):
                self.b.consume_from_issue(
                    self.issue,
                    quantity=quantity,
                    expected_version=0,
                    updated_at=self.fx.at,
                )

    def test_part_cannot_exceed_current_layer_balance(self) -> None:
        """Допустимая по ISSUE часть всё равно ограничена текущим остатком выбранного слоя."""
        with self.assertRaises(ValuationLayerConsumptionError):
            self.a.consume_from_issue(
                self.issue,
                quantity=QuantityVO(Decimal(4)),
                expected_version=0,
                updated_at=self.fx.at,
            )
        self.assertEqual(self.a.remaining_qty.value, Decimal(3))

    def test_partial_transition_retains_strict_version_control(self) -> None:
        """Частичное количество не ослабляет проверку ожидаемой версии."""
        with self.assertRaises(ValuationLayerVersionConflictError):
            self.after_b.consume_from_issue(
                self.issue,
                quantity=QuantityVO(Decimal(1)),
                expected_version=0,
                updated_at=self.fx.at,
            )

    def test_under_and_over_allocation_are_rejected(self) -> None:
        """Каждая часть сама допустима, но итог всей группы должен точно равняться семи KG."""
        for quantities in (("3", "3"), ("3", "5")):
            with (
                self.subTest(quantities=quantities),
                self.assertRaises(ValuationPostingSourceError),
            ):
                self.create(consumptions=self.parts(*quantities))

    def test_missing_part_does_not_create_partial_valuation_posting(self) -> None:
        """Наличие хотя бы одного результата на Ledger недостаточно для полного стоимостного проведения."""
        with self.assertRaises(ValuationPostingSourceError):
            self.create(consumptions=(self.part_a,), entry_bindings=(self.bindings[0],))

    def test_same_layer_cannot_appear_twice_even_with_sequential_versions(self) -> None:
        """Несколько вызовов потребления слоя не заменяют одно итоговое потребление на проведение."""
        changed, first = self.b.consume_from_issue(
            self.issue,
            quantity=QuantityVO(Decimal(3)),
            expected_version=0,
            updated_at=self.fx.at,
        )
        _, second = changed.consume_from_issue(
            self.issue,
            quantity=QuantityVO(Decimal(4)),
            expected_version=1,
            updated_at=self.fx.at,
        )
        with self.assertRaises(DuplicateValuationEntryError):
            self.create(
                consumptions=(first, second), entry_bindings=(self.bindings[1],)
            )

    def test_stable_group_order_uses_layer_id_not_input_order(self) -> None:
        """Порядок частей определяется ID слоя и не объявляет автоматический FIFO."""
        forward = self.create()
        reverse = self.create(
            consumptions=(self.part_b, self.part_a),
            entry_bindings=tuple(reversed(self.bindings)),
        )
        self.assertEqual(forward.entries, reverse.entries)

    def test_multiple_ledger_groups_are_checked_and_ordered_independently(self) -> None:
        """Первая физическая запись получает две части, вторая одну; порядок сохраняется по Ledger."""
        context = self.base.multiple_context()
        first, second = context["consumptions"]
        results = tuple(
            layer.consume_from_issue(
                first.issue,
                quantity=QuantityVO(Decimal(1)),
                expected_version=0,
                updated_at=self.fx.at,
            )[1]
            for layer in (self.a, self.b)
        )
        context.update(
            consumptions=(second, results[1], results[0]),
            entry_bindings=(*self.bindings, context["entry_bindings"][1]),
        )
        posting = self.create(**context)
        self.assertEqual(
            [entry.ledger_entry_id for entry in posting.entries],
            [
                first.issue.ledger_entry_id,
                first.issue.ledger_entry_id,
                second.issue.ledger_entry_id,
            ],
        )

    def test_restore_accepts_valid_expense_group_without_external_context(self) -> None:
        """Согласованная группа разных слоёв восстанавливается из собственных полей журнала."""
        posting = self.create()
        self.assertEqual(self.base.restore(posting), posting)

    def test_restore_rejects_conflicting_dimensions_inside_group(self) -> None:
        """Повтор Ledger допускается только при одинаковых позиции, товаре, владельце, складе и единице."""
        posting = self.create()
        a, b = posting.entries
        for changes in (
            dict(position_id=StockPositionIdVO(uuid4())),
            dict(inventory_item_id=InventoryItemIdVO(uuid4())),
            dict(owner_id=StockOwnerIdVO(uuid4())),
            dict(warehouse_id=WarehouseIdVO(uuid4())),
            dict(base_uom=UomCodeVO("G")),
        ):
            with (
                self.subTest(changes=changes),
                self.assertRaises(DuplicateValuationEntryError),
            ):
                self.base.restore(posting, entries=(a, replace(b, **changes)))

    def test_restore_rejects_one_position_under_different_ledger_ids(self) -> None:
        """Одна исходная позиция не может быть распределена между разными группами физического Ledger."""
        posting = self.create()
        a, b = posting.entries
        with self.assertRaises(DuplicateValuationEntryError):
            self.base.restore(
                posting,
                entries=(a, replace(b, ledger_entry_id=StockLedgerEntryIdVO(uuid4()))),
            )

    def test_entry_ids_and_layers_remain_unique_within_group(self) -> None:
        """Разрешение нескольких частей не разрешает повтор ID записи или слоя."""
        posting = self.create()
        a, b = posting.entries
        for changes in (dict(id=a.id), dict(layer_id=a.layer_id)):
            with self.assertRaises(DuplicateValuationEntryError):
                self.base.restore(posting, entries=(a, replace(b, **changes)))

    def test_receipt_retains_strict_ledger_and_position_uniqueness(self) -> None:
        """Многослойные расходные группы не ослабляют прежние правила прихода."""
        posting = self.create()
        entries = tuple(
            self.base.restore_entry(
                entry,
                quantity_delta=StockDeltaVO(entry.quantity_delta.value.copy_abs()),
                cost_delta=MoneyVO(
                    entry.cost_delta.amount.copy_abs(), entry.cost_delta.currency
                ),
            )
            for entry in posting.entries
        )
        with self.assertRaises(DuplicateValuationEntryError):
            self.base.restore(
                posting, operation_type=StockOperationType.RECEIPT, entries=entries
            )

    def test_each_part_is_compared_to_same_physical_issue(self) -> None:
        """Самосогласованное основание другой даты в одной части не проходит повторную проверку Ledger."""
        changed = replace(
            self.part_b,
            issue=replace(
                self.issue, issued_at=self.issue.issued_at + timedelta(minutes=1)
            ),
        )
        changed.ensure_valid()
        with self.assertRaises(ValuationPostingSourceError):
            self.create(consumptions=(self.part_a, changed))

    def test_result_keeps_quantity_difference_and_cost_proofs_for_partial_issue(
        self,
    ) -> None:
        """Уменьшение части не проходит без согласованного изменения количественных и денежных остатков."""
        for changes in (
            dict(quantity=QuantityVO(Decimal(2))),
            dict(cost=MoneyVO(Decimal(47), CurrencyVO("UAH"))),
            dict(quantity=QuantityVO(Decimal(8))),
        ):
            with (
                self.subTest(changes=changes),
                self.assertRaises(InvalidValuationLayerConsumptionSnapshotError),
            ):
                replace(self.part_b, **changes).ensure_valid()

    def test_different_currencies_in_one_ledger_group_remain_separate(self) -> None:
        """Количество группы складывается точно, а денежные суммы разных валют не объединяются."""
        layer = self.layer("10", "120", 200, "EUR")
        _, part = layer.consume_from_issue(
            self.issue,
            quantity=QuantityVO(Decimal(4)),
            expected_version=0,
            updated_at=self.fx.at,
        )
        posting = self.create(consumptions=(self.part_a, part))
        self.assertEqual(
            [entry.cost_delta.currency for entry in posting.entries],
            [CurrencyVO("UAH"), CurrencyVO("EUR")],
        )

    def test_zero_cost_parts_are_preserved_in_group(self) -> None:
        """Бесплатный слой и округлённый до нуля расход не теряют свои количественные записи."""
        layers = (self.layer("3", ".0001", 100), self.layer("10", "0", 200))
        parts = tuple(
            layer.consume_from_issue(
                self.issue,
                quantity=QuantityVO(Decimal(q)),
                expected_version=0,
                updated_at=self.fx.at,
            )[1]
            for layer, q in zip(layers, ("1", "6"))
        )
        posting = self.create(consumptions=parts)
        self.assertEqual(
            [entry.cost_delta.amount for entry in posting.entries],
            [Decimal(0), Decimal(0)],
        )
        self.assertEqual(
            [entry.quantity_delta.value for entry in posting.entries],
            [Decimal(-1), Decimal(-6)],
        )

    def test_hostile_decimal_context_preserves_exact_fractional_sum_and_costs(
        self,
    ) -> None:
        """Дробные части суммируются без внешнего округления; каждый слой оценивается своей накопленной формулой."""
        with localcontext() as ctx:
            ctx.prec = 1
            ctx.traps[Inexact] = True
            ctx.traps[Rounded] = True
            posting = self.create(consumptions=self.parts(".123456789", "6.876543211"))
        self.assertEqual(
            [entry.quantity_delta.value for entry in posting.entries],
            list(map(Decimal, ("-.123456789", "-6.876543211"))),
        )
        self.assertEqual(
            [entry.cost_delta.amount for entry in posting.entries],
            list(map(Decimal, ("-1.2346", "-82.5185"))),
        )

    def test_serial_identifier_is_derived_and_full_consumption_remains_valid(
        self,
    ) -> None:
        """Снимок сохраняет ID серии; полная одна PCS по-прежнему потребляется одним слоем."""
        layer, position, stock, issue = self.serial_context()
        self.assertEqual(issue.serial_id, position.dimensions.serial_id)
        for quantity in (None, QuantityVO(Decimal(1))):
            after, result = layer.consume_from_issue(
                issue, quantity=quantity, expected_version=0, updated_at=self.fx.at
            )
            self.assertTrue(after.is_exhausted())
            posting = self.create(
                posting=stock.snapshot(),
                consumptions=(result,),
                positions=(position.snapshot(),),
                entry_bindings=(
                    ValuationEntryBindingVO(layer.id, self.bindings[0].entry_id),
                ),
            )
            self.assertEqual(posting.entries[0].quantity_delta.value, Decimal(-1))
        self.assertIsNone(self.issue.serial_id)

    def test_serial_cannot_be_consumed_as_fraction(self) -> None:
        """Одна PCS с конкретной серией не делится на части даже при достаточном остатке слоя."""
        layer, _, _, issue = self.serial_context()
        with self.assertRaises(ValuationLayerConsumptionError):
            layer.consume_from_issue(
                issue,
                quantity=QuantityVO(Decimal(".5")),
                expected_version=0,
                updated_at=self.fx.at,
            )

    def test_serial_result_rejects_arithmetically_valid_half(self) -> None:
        """Самосогласованная половина количества и стоимости не является допустимым серийным потреблением."""
        layer, _, _, issue = self.serial_context()
        _, result = layer.consume_from_issue(
            replace(issue, serial_id=None),
            quantity=QuantityVO(Decimal(".5")),
            expected_version=0,
            updated_at=self.fx.at,
        )
        with self.assertRaises(InvalidValuationLayerConsumptionSnapshotError):
            replace(result, issue=issue).ensure_valid()

    def test_serial_cannot_be_hidden_when_registering_two_halves(self) -> None:
        """Повторная проверка физической позиции обнаруживает удалённый из результатов идентификатор серии."""
        layer, position, stock, issue = self.serial_context()
        hidden = replace(issue, serial_id=None)
        parts = tuple(
            replace(layer, id=ValuationLayerIdVO(uuid4())).consume_from_issue(
                hidden,
                quantity=QuantityVO(Decimal(".5")),
                expected_version=0,
                updated_at=self.fx.at,
            )[1]
            for _ in range(2)
        )
        with self.assertRaises(ValuationPostingSourceError):
            self.create(
                posting=stock.snapshot(),
                consumptions=parts,
                positions=(position.snapshot(),),
                entry_bindings=tuple(
                    ValuationEntryBindingVO(part.layer.id, ValuationEntryIdVO(uuid4()))
                    for part in parts
                ),
            )

    def test_issue_snapshot_requires_nominal_serial_and_one_pcs(self) -> None:
        """Явный serial_id проверяется по типу, единице и полному количеству физического расхода."""
        _, _, _, issue = self.serial_context()
        for changes in (
            dict(serial_id=uuid4()),
            dict(serial_id="serial"),
            dict(base_uom=UomCodeVO("KG")),
            dict(quantity=QuantityVO(Decimal(2))),
        ):
            with self.subTest(changes=changes), self.assertRaises(InventoryError):
                replace(issue, **changes).ensure_valid()

    def test_group_registration_does_not_reconsume_or_mutate_originals(self) -> None:
        """Регистрация нескольких частей не меняет исходные слои, новые остатки и физический журнал."""
        self.create()
        self.assertEqual((self.a.version, self.b.version), (0, 0))
        self.assertEqual((self.after_a.version, self.after_b.version), (1, 1))
        self.assertEqual(self.after_b.remaining_qty.value, Decimal(6))
        self.assertEqual(len(self.stock.entries), 1)
        self.assertEqual(self.f.first.version, 0)


if __name__ == "__main__":
    unittest.main()
