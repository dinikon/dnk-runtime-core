"""FIFO-план одной записи ISSUE, проверка сохранённого пула и применение версий слоёв."""

import unittest
from dataclasses import FrozenInstanceError, replace
from datetime import timedelta, timezone
from decimal import Decimal, Inexact, Rounded, localcontext
from uuid import uuid4

from test import test_inventory_layer_split_domain as split_fixture
from src.modules.inventory.domain.error import InventoryError
from src.modules.inventory.domain.inventory_item.value_object.identifier import (
    InventoryItemIdVO,
)
from src.modules.inventory.domain.stock_position.value_object.identifier import (
    StockPositionIdVO,
)
from src.modules.inventory.domain.stock_posting.fifo_plan_snapshot import (
    StockIssueFifoPlanSnapshot,
)
from src.modules.inventory.domain.valuation_layer.aggregate import ValuationLayer
from src.modules.inventory.domain.valuation_layer.error import (
    InsufficientValuationFifoQuantityError,
    InvalidStockIssueFifoPlanError,
    InvalidValuationIssueAllocationError,
    ValuationFifoStateConflictError,
    ValuationLayerVersionConflictError,
)
from src.modules.inventory.domain.valuation_layer.value_object.cost_basis import (
    CostBasisVO,
)
from src.modules.inventory.domain.valuation_layer.value_object.issue_allocation import (
    ValuationLayerIssueAllocationVO,
)
from src.modules.inventory.domain.value_object.quantity import QuantityVO
from src.modules.inventory.domain.value_object.stock_owner_id import StockOwnerIdVO
from src.modules.inventory.domain.value_object.uom_code import UomCodeVO
from src.modules.inventory.domain.warehouse.value_object.identifier import WarehouseIdVO
from src.modules.shared.domain.value_object.currency import CurrencyVO
from src.modules.shared.domain.value_object.money import MoneyVO


class InventoryFifoDomainTests(unittest.TestCase):
    """Проверяет чистый выбор FIFO и применение через существующий стоимостной переход слоя."""

    def setUp(self) -> None:
        """Готовит ISSUE семи KG и два слоя одной позиции с остатками три и десять KG."""
        self.s = split_fixture.LayerSplitDomainTests()
        self.s.setUp()
        self.a = self.s.a
        self.b = self.s.b
        self.issue = self.s.issue
        self.at = self.s.fx.at

    def plan(
        self, layers: tuple[ValuationLayer, ...] | None = None, **changes: object
    ) -> StockIssueFifoPlanSnapshot:
        """Строит план из настоящих снимков корней без передачи чужих агрегатов в Policy."""
        selected = (self.a, self.b) if layers is None else layers
        return StockIssueFifoPlanSnapshot.create(
            **(
                dict(
                    issue=self.issue,
                    candidates=tuple(layer.fifo_snapshot() for layer in selected),
                )
                | changes
            )
        )

    def test_snapshot_captures_complete_current_state_and_basis(self) -> None:
        """Кандидат содержит первоначальное основание, текущие количество, деньги, версию и момент изменения."""
        snapshot = self.s.after_b.fifo_snapshot()
        self.assertEqual(snapshot.layer, self.b.receipt_valuation_snapshot())
        self.assertEqual(snapshot.remaining_qty, QuantityVO(Decimal(6)))
        self.assertEqual(
            snapshot.remaining_cost, MoneyVO(Decimal(72), CurrencyVO("UAH"))
        )
        self.assertEqual(snapshot.version, 1)
        self.assertEqual(snapshot.updated_at, self.at)
        snapshot.ensure_valid()

    def test_fifo_allocates_full_issue_across_layers_with_captured_versions(
        self,
    ) -> None:
        """Слои три и десять KG покрывают семь как три плюс четыре с версиями ноль."""
        plan = self.plan()
        self.assertEqual(
            [
                (part.layer_id, part.quantity.value, part.expected_version)
                for part in plan.allocations
            ],
            [(self.a.id, Decimal(3), 0), (self.b.id, Decimal(4), 0)],
        )
        plan.ensure_valid()

    def test_received_time_has_priority_over_uuid_and_cost_registration_time(
        self,
    ) -> None:
        """Более раннее физическое поступление выбирается раньше меньшего UUID и более ранней регистрации цены."""
        late_a = self.s.fx.v.restore(
            self.a, received_at=self.a.received_at + timedelta(minutes=1)
        )
        late_priced_b = self.s.fx.v.restore(
            self.b,
            created_at=self.at + timedelta(hours=1),
            updated_at=self.at + timedelta(hours=1),
        )
        plan = self.plan((late_a, late_priced_b))
        self.assertEqual(
            [allocation.layer_id for allocation in plan.allocations], [self.b.id]
        )
        changed, _ = late_priced_b.consume_fifo_allocation(
            plan, updated_at=self.at + timedelta(hours=1)
        )
        self.assertEqual(changed.remaining_qty.value, Decimal(3))

    def test_equal_receipt_times_use_uuid_and_input_permutation_has_no_effect(
        self,
    ) -> None:
        """Одинаковые даты разрешаются UUID слоя, а порядок переданных кандидатов ничего не меняет."""
        first = self.plan((self.b, self.a))
        self.assertEqual(first.allocations, self.plan().allocations)
        self.assertEqual(first.allocations[0].layer_id, self.a.id)

    def test_exhausted_candidate_is_valid_but_not_selected(self) -> None:
        """Исчерпанный слой остаётся частью снимка пула, но не получает назначения."""
        exhausted = self.s.after_a
        plan = self.plan((exhausted, self.b))
        self.assertEqual([a.layer_id for a in plan.allocations], [self.b.id])
        self.assertEqual(plan.allocations[0].quantity.value, Decimal(7))

    def test_free_or_rounded_zero_cost_layer_is_still_available(self) -> None:
        """FIFO учитывает количество, включая бесплатный остаток и остаток с округлённой нулевой стоимостью."""
        for layer in (
            self.s.layer("3", "0", 100),
            self.s.layer("3", ".0001", 100).consume(
                QuantityVO(Decimal(2)), expected_version=0, updated_at=self.at
            ),
        ):
            plan = self.plan((layer, self.b))
            self.assertEqual(plan.allocations[0].layer_id, layer.id)
            self.assertEqual(plan.allocations[0].quantity, layer.remaining_qty)

    def test_insufficient_or_empty_pool_never_returns_partial_plan(self) -> None:
        """План либо полностью покрывает ISSUE, либо отклоняет весь выбор без изменения слоёв."""
        for layers in ((), (self.a,), (self.s.after_a,)):
            with (
                self.subTest(layers=layers),
                self.assertRaises(InsufficientValuationFifoQuantityError),
            ):
                self.plan(layers)
        self.assertEqual((self.a.version, self.b.version), (0, 0))

    def test_pool_rejects_raw_types_and_mutable_collections(self) -> None:
        """Планирование принимает только специализированные снимки и immutable tuple."""
        for changes in (
            dict(issue=None),
            dict(candidates=[self.a.fifo_snapshot()]),
            dict(candidates=(self.a,)),
            dict(candidates=(None,)),
        ):
            with (
                self.subTest(changes=changes),
                self.assertRaises(InvalidStockIssueFifoPlanError),
            ):
                self.plan(**changes)

    def test_pool_rejects_duplicate_layer_or_receipt_source(self) -> None:
        """Повтор ID слоя или повторное представление одной записи поступления не увеличивает доступность."""
        a = self.a.fifo_snapshot()
        b = self.b.fifo_snapshot()
        duplicate_source = replace(b, layer=replace(b.layer, source=a.layer.source))
        for candidates in ((a, a), (a, duplicate_source)):
            with self.assertRaises(InvalidStockIssueFifoPlanError):
                self.plan(candidates=candidates)

    def test_pool_rejects_foreign_position_item_owner_warehouse_or_unit(self) -> None:
        """Полный пул должен относиться к одной исходной позиции и учётным измерениям ISSUE."""
        a = self.a.fifo_snapshot()
        for changes in (
            dict(
                source=replace(a.layer.source, position_id=StockPositionIdVO(uuid4()))
            ),
            dict(inventory_item_id=InventoryItemIdVO(uuid4())),
            dict(owner_id=StockOwnerIdVO(uuid4())),
            dict(warehouse_id=WarehouseIdVO(uuid4())),
            dict(base_uom=UomCodeVO("G")),
        ):
            with self.subTest(changes=changes), self.assertRaises(InventoryError):
                self.plan(
                    candidates=(
                        replace(a, layer=replace(a.layer, **changes)),
                        self.b.fifo_snapshot(),
                    )
                )

    def test_future_receipt_is_rejected_even_when_not_needed_for_quantity(self) -> None:
        """Проверяется весь переданный контекст, включая невыбираемые будущие слои."""
        future = self.s.fx.v.restore(
            self.a,
            received_at=self.issue.issued_at + timedelta(minutes=1),
            created_at=self.at,
            updated_at=self.at,
        )
        with self.assertRaises(InventoryError):
            self.plan((self.b, future))

    def test_snapshot_rejects_wrong_basis_version_cost_and_quantity(self) -> None:
        """Снимок кандидата повторно проверяет собственную стоимость, количество и строгую версию."""
        candidate = self.a.fifo_snapshot()
        for changes in (
            dict(layer=None),
            dict(version=True),
            dict(version=-1),
            dict(remaining_qty=QuantityVO(Decimal(4))),
            dict(remaining_cost=MoneyVO(Decimal(29), CurrencyVO("UAH"))),
            dict(remaining_cost=MoneyVO(Decimal(30), CurrencyVO("EUR"))),
            dict(remaining_cost=self.s.fx.malformed_money(Decimal("NaN"))),
        ):
            with self.subTest(changes=changes), self.assertRaises(InventoryError):
                replace(candidate, **changes).ensure_valid()

    def test_snapshot_requires_saved_utc_update_not_before_creation(self) -> None:
        """Готовое состояние FIFO хранит UTC и не предшествует созданию слоя."""
        candidate = self.a.fifo_snapshot()
        for at in (
            None,
            self.at.replace(tzinfo=None),
            candidate.layer.created_at - timedelta(seconds=1),
            self.at.astimezone(timezone(timedelta(hours=2))),
        ):
            with self.subTest(at=at), self.assertRaises(InventoryError):
                replace(candidate, updated_at=at).ensure_valid()

    def test_snapshot_export_revalidates_root(self) -> None:
        """Повреждённый корень не экспортирует внешне корректный снимок FIFO."""
        broken = replace(self.a, remaining_cost=MoneyVO(Decimal(0), CurrencyVO("UAH")))
        with self.assertRaises(InventoryError):
            broken.fifo_snapshot()

    def test_allocation_vo_requires_nominal_positive_quantity_and_strict_version(
        self,
    ) -> None:
        """Назначение не допускает сырой ID, неположительное количество и булеву либо дробную версию."""
        for layer_id, quantity, version in (
            (uuid4(), QuantityVO(Decimal(1)), 0),
            (self.a.id, Decimal(1), 0),
            (self.a.id, QuantityVO(Decimal(0)), 0),
            (self.a.id, self.s.fx.malformed_quantity(Decimal("NaN")), 0),
            (self.a.id, QuantityVO(Decimal(1)), True),
            (self.a.id, QuantityVO(Decimal(1)), -1),
            (self.a.id, QuantityVO(Decimal(1)), 0.0),
        ):
            with (
                self.subTest(version=version),
                self.assertRaises(InvalidValuationIssueAllocationError),
            ):
                ValuationLayerIssueAllocationVO(layer_id, quantity, version)

    def test_plan_rejects_changed_quantity_order_version_or_missing_old_layer(
        self,
    ) -> None:
        """Даже полное количество не позволяет обойти более старый слой или изменить версии назначений."""
        plan = self.plan()
        a, b = plan.allocations
        alternatives = (
            (
                replace(a, quantity=QuantityVO(Decimal(2))),
                replace(b, quantity=QuantityVO(Decimal(5))),
            ),
            (b, a),
            (replace(b, quantity=self.issue.quantity),),
            (replace(a, expected_version=1), b),
            (a,),
            (),
        )
        for allocations in alternatives:
            with (
                self.subTest(allocations=allocations),
                self.assertRaises(InvalidStockIssueFifoPlanError),
            ):
                replace(plan, allocations=allocations).ensure_valid()

    def test_plan_rejects_wrong_allocation_types_and_corrupted_vo(self) -> None:
        """Повторная проверка плана не доверяет mutable коллекции или повреждённому назначению."""
        plan = self.plan()
        bad = object.__new__(ValuationLayerIssueAllocationVO)
        object.__setattr__(bad, "layer_id", self.a.id)
        object.__setattr__(bad, "quantity", QuantityVO(Decimal(3)))
        object.__setattr__(bad, "expected_version", False)
        for allocations in ([*plan.allocations], (None,), (bad, plan.allocations[1])):
            with (
                self.subTest(allocations=allocations),
                self.assertRaises(InventoryError),
            ):
                replace(plan, allocations=allocations).ensure_valid()

    def test_plan_and_candidates_and_allocations_are_immutable(self) -> None:
        """План и вложенные контракты не предоставляют прямого изменения состояния."""
        plan = self.plan()
        for obj, name, value in (
            (plan, "allocations", ()),
            (plan.candidates[0], "version", 10),
            (plan.allocations[0], "expected_version", 10),
        ):
            with self.assertRaises(FrozenInstanceError):
                setattr(obj, name, value)

    def test_apply_selected_layers_returns_existing_consumption_results(self) -> None:
        """Один план применяется к каждому выбранному слою и использует прежний расчёт стоимости."""
        plan = self.plan()
        a, result_a = self.a.consume_fifo_allocation(plan, updated_at=self.at)
        b, result_b = self.b.consume_fifo_allocation(plan, updated_at=self.at)
        self.assertEqual((a, b), (self.s.after_a, self.s.after_b))
        self.assertEqual((result_a, result_b), (self.s.part_a, self.s.part_b))
        posting = self.s.create(consumptions=(result_a, result_b))
        self.assertEqual(
            [entry.cost_delta.amount for entry in posting.entries],
            [Decimal(-30), Decimal(-48)],
        )
        self.assertEqual((self.a.version, self.b.version), (0, 0))
        self.assertEqual(len(self.s.stock.entries), 1)
        self.assertEqual(self.s.f.first.version, 0)

    def test_repeated_apply_or_changed_version_is_rejected(self) -> None:
        """Ожидаемая версия берётся из плана и не подменяется текущим значением слоя."""
        plan = self.plan()
        changed, _ = self.a.consume_fifo_allocation(plan, updated_at=self.at)
        with self.assertRaises(ValuationLayerVersionConflictError):
            changed.consume_fifo_allocation(plan, updated_at=self.at)

    def test_same_version_with_different_state_is_rejected(self) -> None:
        """Совпадения версии недостаточно при изменённых остатках, основании или времени кандидата."""
        plan = self.plan()
        for changes in (
            dict(
                remaining_qty=QuantityVO(Decimal(2)),
                remaining_cost=MoneyVO(Decimal(20), CurrencyVO("UAH")),
            ),
            dict(updated_at=self.a.updated_at + timedelta(minutes=1)),
            dict(
                cost_basis=CostBasisVO(
                    QuantityVO(Decimal(3)), MoneyVO(Decimal(31), CurrencyVO("UAH"))
                ),
                remaining_cost=MoneyVO(Decimal(31), CurrencyVO("UAH")),
            ),
        ):
            current = self.s.fx.v.restore(self.a, **changes)
            with (
                self.subTest(changes=changes),
                self.assertRaises(ValuationFifoStateConflictError),
            ):
                current.consume_fifo_allocation(plan, updated_at=self.at)

    def test_unselected_or_absent_layer_cannot_apply_plan(self) -> None:
        """Совместимый слой не потребляется, если план не назначил ему количество."""
        plan = self.plan(issue=replace(self.issue, quantity=QuantityVO(Decimal(2))))
        for layer in (self.b, self.s.layer("10", "120", 300)):
            with self.assertRaises(ValuationFifoStateConflictError):
                layer.consume_fifo_allocation(plan, updated_at=self.at)

    def test_apply_revalidates_plan_before_changing_any_state(self) -> None:
        """Подмена назначения или отсутствие специализированного плана не создаёт новый слой."""
        plan = self.plan()
        bad = replace(plan, allocations=tuple(reversed(plan.allocations)))
        for value in (None, bad):
            with self.assertRaises(InvalidStockIssueFifoPlanError):
                self.a.consume_fifo_allocation(value, updated_at=self.at)
        self.assertEqual(self.a.version, 0)

    def test_apply_preserves_existing_time_validation_and_normalization(self) -> None:
        """Применение FIFO требует явное время не раньше ISSUE и нормализует смещение в UTC."""
        plan = self.plan()
        for at in (
            None,
            self.at.replace(tzinfo=None),
            self.issue.issued_at - timedelta(seconds=1),
        ):
            with self.assertRaises(InventoryError):
                self.a.consume_fifo_allocation(plan, updated_at=at)
        changed, _ = self.a.consume_fifo_allocation(
            plan, updated_at=self.at.astimezone(timezone(timedelta(hours=2)))
        )
        self.assertEqual(changed.updated_at, self.at)

    def test_serial_fifo_selects_and_consumes_one_whole_pcs(self) -> None:
        """Серийный ISSUE получает ровно один полный слой и сохраняет прежнюю неделимость экземпляра."""
        layer, _, _, issue = self.s.serial_context()
        plan = self.plan((layer,), issue=issue)
        self.assertEqual(len(plan.allocations), 1)
        self.assertEqual(plan.allocations[0].quantity.value, Decimal(1))
        changed, result = layer.consume_fifo_allocation(plan, updated_at=self.at)
        self.assertTrue(changed.is_exhausted())
        self.assertEqual(result.issue.serial_id, issue.serial_id)

    def test_serial_pool_rejects_fractional_remaining_or_original_quantity(
        self,
    ) -> None:
        """Два дробных остатка не заменяют один целый серийный слой."""
        layer, _, _, issue = self.s.serial_context()
        fractional = layer.consume(
            QuantityVO(Decimal(".5")), expected_version=0, updated_at=self.at
        )
        wrong_basis = self.s.fx.v.restore(
            layer,
            cost_basis=CostBasisVO(QuantityVO(Decimal(2)), layer.cost_basis.total_cost),
            remaining_qty=QuantityVO(Decimal(2)),
        )
        for candidate in (fractional, wrong_basis):
            with self.assertRaises(InvalidStockIssueFifoPlanError):
                self.plan((candidate,), issue=issue)

    def test_partial_layers_keep_expected_versions_and_cumulative_rounding(
        self,
    ) -> None:
        """Новые планы читают новые версии, а три расхода сохраняют накопленные .3333, .3334, .3333."""
        layer, position = self.s.fx.case("3", "1", "PCS")
        costs = []
        for version in range(3):
            issue = self.s.fx.produce(
                self.s.fx.issue_for("1", position), position=position.snapshot()
            )
            plan = self.plan((layer,), issue=issue)
            self.assertEqual(plan.allocations[0].expected_version, version)
            layer, result = layer.consume_fifo_allocation(plan, updated_at=self.at)
            costs.append(result.cost.amount)
        self.assertEqual(costs, list(map(Decimal, (".3333", ".3334", ".3333"))))
        self.assertTrue(layer.is_exhausted())

    def test_different_currency_does_not_affect_fifo_choice(self) -> None:
        """FIFO не сравнивает валюты или цены, а результаты сохраняют стоимость каждого слоя отдельно."""
        b = self.s.layer("10", "120", 200, "EUR")
        plan = self.plan((b, self.a))
        _, first = self.a.consume_fifo_allocation(plan, updated_at=self.at)
        _, second = b.consume_fifo_allocation(plan, updated_at=self.at)
        posting = self.s.create(consumptions=(first, second))
        self.assertEqual(
            [entry.cost_delta.currency for entry in posting.entries],
            [CurrencyVO("UAH"), CurrencyVO("EUR")],
        )

    def test_hostile_decimal_context_does_not_round_allocation_or_cost(self) -> None:
        """Точные дробные остатки планируются и потребляются независимо от внешней точности и traps."""
        a = self.a.consume(
            QuantityVO(Decimal("2.876543211")), expected_version=0, updated_at=self.at
        )
        with localcontext() as ctx:
            ctx.prec = 1
            ctx.traps[Inexact] = True
            ctx.traps[Rounded] = True
            plan = self.plan((a, self.b))
            _, first = a.consume_fifo_allocation(plan, updated_at=self.at)
            _, second = self.b.consume_fifo_allocation(plan, updated_at=self.at)
            plan.ensure_valid()
        self.assertEqual(
            [allocation.quantity.value for allocation in plan.allocations],
            list(map(Decimal, (".123456789", "6.876543211"))),
        )
        self.assertEqual(second.cost.amount, Decimal("82.5185"))
        self.assertEqual(first.quantity.value, Decimal(".123456789"))


if __name__ == "__main__":
    unittest.main()
