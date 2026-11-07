"""Полное FIFO-основание ISSUE и регистрация ровно его результатов потребления."""

import unittest
from dataclasses import FrozenInstanceError, fields, replace
from datetime import timedelta
from decimal import Decimal, Inexact, Rounded, localcontext
from uuid import uuid4

from test import test_inventory_layer_split_domain as split_fixture
from src.modules.inventory.domain.error import InventoryError
from src.modules.inventory.domain.stock_posting.aggregate import StockPosting
from src.modules.inventory.domain.stock_posting.error import (
    InvalidStockPostingFifoPlanError,
)
from src.modules.inventory.domain.stock_posting.fifo_plan_snapshot import (
    StockIssueFifoPlanSnapshot,
)
from src.modules.inventory.domain.stock_posting.posting_fifo_plan_snapshot import (
    StockPostingFifoPlanSnapshot,
)
from src.modules.inventory.domain.stock_posting.snapshot import StockPostingSnapshot
from src.modules.inventory.domain.stock_posting.value_object.operation_type import (
    StockOperationType,
)
from src.modules.inventory.domain.stock_posting.value_object.posting_source import (
    PostingSourceVO,
)
from src.modules.inventory.domain.stock_execution.value_object.identifier import (
    StockExecutionIdVO,
)
from src.modules.inventory.domain.stock_position.aggregate import StockPosition
from src.modules.inventory.domain.stock_position.value_object.identifier import (
    StockPositionIdVO,
)
from src.modules.inventory.domain.valuation_layer.aggregate import ValuationLayer
from src.modules.inventory.domain.valuation_layer.consumption_snapshot import (
    ValuationLayerConsumptionSnapshot,
)
from src.modules.inventory.domain.valuation_layer.error import (
    InsufficientValuationFifoQuantityError,
)
from src.modules.inventory.domain.valuation_layer.fifo_snapshot import (
    ValuationLayerFifoSnapshot,
)
from src.modules.inventory.domain.valuation_layer.value_object.cost_basis import (
    CostBasisVO,
)
from src.modules.inventory.domain.valuation_layer.value_object.identifier import (
    ValuationLayerIdVO,
)
from src.modules.inventory.domain.value_object.uom_code import UomCodeVO
from src.modules.inventory.domain.valuation_posting.aggregate import ValuationPosting
from src.modules.inventory.domain.valuation_posting.error import (
    ValuationPostingSourceError,
    ValuationPostingTimeError,
)
from src.modules.inventory.domain.valuation_posting.value_object.identifier import (
    ValuationPostingIdVO,
)
from src.modules.inventory.domain.value_object.quantity import QuantityVO
from src.modules.inventory.domain.value_object.quantity_conversion_snapshot import (
    QuantityConversionSnapshotVO,
)
from src.modules.inventory.domain.value_object.stock_owner_id import StockOwnerIdVO
from src.modules.shared.domain.value_object.currency import CurrencyVO
from src.modules.shared.domain.value_object.money import MoneyVO


class PostingFifoDomainTests(unittest.TestCase):
    """Проверяет полное покрытие нескольких записей и соответствие журнала конкретному FIFO-решению."""

    def setUp(self) -> None:
        """Готовит расход семи KG из двух слоёв и четырёх PCS другой позиции в USD."""
        self.s = split_fixture.LayerSplitDomainTests()
        self.s.setUp()
        self.context = self.s.base.multiple_context()
        second = self.context["positions"][1]
        self.second_position = StockPosition.restore(
            identifier=second.id,
            dimensions=second.dimensions,
            base_uom=second.base_uom,
            on_hand_qty=QuantityVO(Decimal(0)),
            version=0,
        )
        self.stock = self.s.fx.issue_for(
            "7",
            entries=(self.s.f.entry("-7"), self.s.f.entry("-4", self.second_position)),
            positions=self.context["positions"],
        )
        result = self.context["consumptions"][1]
        self.third = ValuationLayerFifoSnapshot(
            result.layer,
            result.remaining_qty_before,
            result.remaining_cost_before,
            result.version_before,
            result.updated_at_before,
        )
        self.candidates = (
            self.s.a.fifo_snapshot(),
            self.s.b.fifo_snapshot(),
            self.third,
        )
        self.bindings = (*self.s.bindings, self.context["entry_bindings"][1])
        self.plan = self.build()
        self.results = self.apply()

    def build(self, **changes: object) -> StockPostingFifoPlanSnapshot:
        """Строит весь план публичным методом StockPosting по полному контексту."""
        return self.stock.issue_fifo_plan(
            **(
                dict(
                    candidates=self.candidates,
                    positions=self.context["positions"],
                    locations=self.context["locations"],
                )
                | changes
            )
        )

    def layer(self, candidate: ValuationLayerFifoSnapshot) -> ValuationLayer:
        """Восстанавливает собственное состояние слоя для применения исторически зафиксированного назначения."""
        basis = candidate.layer
        return ValuationLayer.restore(
            identifier=basis.id,
            source=basis.source,
            inventory_item_id=basis.inventory_item_id,
            owner_id=basis.owner_id,
            warehouse_id=basis.warehouse_id,
            base_uom=basis.base_uom,
            cost_basis=basis.cost_basis,
            received_at=basis.received_at,
            created_at=basis.created_at,
            remaining_qty=candidate.remaining_qty,
            remaining_cost=candidate.remaining_cost,
            version=candidate.version,
            updated_at=candidate.updated_at,
        )

    def apply(
        self, plan: StockPostingFifoPlanSnapshot | None = None
    ) -> tuple[ValuationLayerConsumptionSnapshot, ...]:
        """Применяет выбранные назначения существующим методом слоя без нового сценария оркестрации."""
        target = self.plan if plan is None else plan
        results = []
        for item in target.plans:
            by_id = {candidate.layer.id: candidate for candidate in item.candidates}
            for allocation in item.allocations:
                _, result = self.layer(
                    by_id[allocation.layer_id]
                ).consume_fifo_allocation(item, updated_at=self.s.fx.at)
                results.append(result)
        return tuple(results)

    def create(self, **changes: object) -> ValuationPosting:
        """Регистрирует весь расход только по точным результатам сохранённого FIFO-плана."""
        return ValuationPosting.create_from_fifo_plan(
            **(
                dict(
                    identifier=ValuationPostingIdVO(uuid4()),
                    plan=self.plan,
                    posting=self.stock.snapshot(),
                    consumptions=self.results,
                    entry_bindings=self.bindings,
                    positions=self.context["positions"],
                    locations=self.context["locations"],
                    posted_at=self.s.base.at,
                )
                | changes
            )
        )

    def restore_stock(
        self, snapshot: StockPostingSnapshot, **changes: object
    ) -> StockPosting:
        """Восстанавливает полный физический факт без пересчёта сохранённых коэффициентов."""
        values = {
            field.name: getattr(snapshot, field.name) for field in fields(snapshot)
        }
        values["identifier"] = values.pop("id")
        return StockPosting.restore(**(values | changes))

    def test_full_plan_covers_ledger_in_order_and_splits_first_position(self) -> None:
        """Для двух записей строятся планы 3+4 KG и 4 PCS с точным исходным проведением."""
        self.assertEqual(self.plan.posting, self.stock.snapshot())
        self.assertEqual(
            [item.issue.ledger_entry_id for item in self.plan.plans],
            [entry.id for entry in self.stock.entries],
        )
        self.assertEqual(
            [
                [part.quantity.value for part in item.allocations]
                for item in self.plan.plans
            ],
            [[Decimal(3), Decimal(4)], [Decimal(4)]],
        )
        self.plan.ensure_valid()

    def test_input_permutation_does_not_change_allocations_or_ledger_order(
        self,
    ) -> None:
        """Порядок глобального пула, позиций и локаций не меняет FIFO-решения записей."""
        other = self.build(
            candidates=tuple(reversed(self.candidates)),
            positions=tuple(reversed(self.context["positions"])),
            locations=tuple(reversed(self.context["locations"])),
        )
        self.assertEqual(
            [(p.issue, p.allocations) for p in other.plans],
            [(p.issue, p.allocations) for p in self.plan.plans],
        )

    def test_missing_quantity_in_any_group_rejects_whole_plan(self) -> None:
        """Успешный план первой записи не позволяет вернуть неполный план всего проведения."""
        for candidates in (
            (),
            self.candidates[:2],
            (self.candidates[0], self.candidates[2]),
        ):
            with (
                self.subTest(candidates=candidates),
                self.assertRaises(InsufficientValuationFifoQuantityError),
            ):
                self.build(candidates=candidates)
        self.assertEqual((self.s.a.version, self.s.b.version), (0, 0))

    def test_foreign_candidate_is_rejected_even_if_all_groups_have_enough(self) -> None:
        """Кандидат несуществующей в ISSUE позиции не игнорируется как неиспользуемый."""
        foreign = self.s.fx.case("3", "30")[0].fifo_snapshot()
        with self.assertRaises(InvalidStockPostingFifoPlanError):
            self.build(candidates=(*self.candidates, foreign))

    def test_global_pool_rejects_duplicate_layer_and_receipt_source(self) -> None:
        """Уникальность слоёв и источников проверяется до разбиения пула по позициям."""
        a, b, c = self.candidates
        for candidate in (
            a,
            replace(c, layer=replace(c.layer, id=a.layer.id)),
            replace(b, layer=replace(b.layer, source=a.layer.source)),
        ):
            with self.assertRaises(InvalidStockPostingFifoPlanError):
                self.build(candidates=(*self.candidates, candidate))

    def test_builder_requires_nominal_candidates_and_tuple_collections(self) -> None:
        """Агрегаты, произвольные элементы и изменяемые коллекции не заменяют контракты."""
        for changes in (
            dict(candidates=[*self.candidates]),
            dict(candidates=(self.s.a,)),
            dict(candidates=(None,)),
            dict(positions=[]),
            dict(locations=[]),
            dict(locations=(None,)),
        ):
            with self.subTest(changes=changes), self.assertRaises(InventoryError):
                self.build(**changes)

    def test_builder_requires_exact_unique_physical_context(self) -> None:
        """Пропуски, лишние снимки и повторы позиций или локаций отклоняются."""
        positions = self.context["positions"]
        locations = self.context["locations"]
        for changes in (
            dict(positions=positions[:1]),
            dict(positions=(positions[0], positions[0])),
            dict(locations=locations[:1]),
            dict(locations=(*locations, locations[0])),
        ):
            with self.assertRaises(InventoryError):
                self.build(**changes)

    def test_receipt_movement_adjustment_and_reversal_cannot_be_planned(self) -> None:
        """Полное FIFO-основание поддерживает только обычный ISSUE."""
        f = self.s.f
        receipt = self.s.fx.v.posting
        adjustment = self.restore_stock(
            self.stock.snapshot(), operation_type=StockOperationType.ADJUSTMENT
        )
        for stock in (
            receipt,
            f.movement(),
            adjustment,
            f.reverse(receipt, posted_at=self.s.fx.issued_at),
        ):
            with (
                self.subTest(operation=stock.operation_type),
                self.assertRaises(InvalidStockPostingFifoPlanError),
            ):
                stock.issue_fifo_plan(
                    candidates=self.candidates,
                    positions=self.context["positions"],
                    locations=self.context["locations"],
                )

    def test_snapshot_rejects_missing_repeated_reordered_or_raw_subplans(self) -> None:
        """Полное основание требует ровно одну согласованную запись плана на каждую строку Ledger в его порядке."""
        first, second = self.plan.plans
        for plans in (
            (),
            (first,),
            (first, first),
            (second, first),
            [first, second],
            (None, second),
        ):
            with (
                self.subTest(plans=plans),
                self.assertRaises(InvalidStockPostingFifoPlanError),
            ):
                replace(self.plan, plans=plans).ensure_valid()

    def test_snapshot_rejects_changed_source_quantity_unit_position_or_time(
        self,
    ) -> None:
        """Согласованный одиночный план не соответствует другому исходному физическому проведению."""
        posting = self.plan.posting
        changed_entry = replace(
            posting.entries[0],
            conversion=QuantityConversionSnapshotVO(
                QuantityVO(Decimal(6)), posting.entries[0].base_uom, Decimal(1)
            ),
            quantity_delta=replace(
                posting.entries[0].quantity_delta, value=Decimal(-6)
            ),
        )
        for source in (
            replace(posting, posted_at=posting.posted_at + timedelta(minutes=1)),
            replace(posting, entries=(changed_entry, posting.entries[1])),
            replace(
                posting,
                entries=(
                    replace(posting.entries[0], position_id=StockPositionIdVO(uuid4())),
                    posting.entries[1],
                ),
            ),
            replace(
                posting,
                entries=(
                    replace(
                        posting.entries[0],
                        base_uom=UomCodeVO("PCS"),
                        conversion=QuantityConversionSnapshotVO(
                            QuantityVO(Decimal(7)), UomCodeVO("PCS"), Decimal(1)
                        ),
                    ),
                    posting.entries[1],
                ),
            ),
        ):
            with self.assertRaises(InvalidStockPostingFifoPlanError):
                replace(self.plan, posting=source).ensure_valid()

    def test_snapshot_checks_candidates_unique_between_individually_valid_plans(
        self,
    ) -> None:
        """Два самостоятельно корректных плана не могут использовать одинаковые ID слоёв или источники."""
        first, second = self.plan.plans
        original = second.candidates[0]
        for layer in (
            replace(original.layer, id=first.candidates[0].layer.id),
            replace(
                original.layer,
                source=replace(
                    original.layer.source,
                    posting_id=first.candidates[0].layer.source.posting_id,
                    ledger_entry_id=first.candidates[0].layer.source.ledger_entry_id,
                ),
            ),
        ):
            changed = StockIssueFifoPlanSnapshot.create(
                issue=second.issue, candidates=(replace(original, layer=layer),)
            )
            with self.assertRaises(InvalidStockPostingFifoPlanError):
                replace(self.plan, plans=(first, changed)).ensure_valid()

    def test_registers_complete_fifo_cost_with_distinct_units_and_currencies(
        self,
    ) -> None:
        """Расходный журнал получает три записи стоимости для двух физических строк без общей суммы валют."""
        posting = self.create()
        self.assertEqual(
            [entry.quantity_delta.value for entry in posting.entries],
            [Decimal(-3), Decimal(-4), Decimal(-4)],
        )
        self.assertEqual(
            [entry.cost_delta.amount for entry in posting.entries],
            [Decimal(-30), Decimal(-48), Decimal(-20)],
        )
        self.assertEqual(
            [entry.cost_delta.currency for entry in posting.entries],
            [CurrencyVO("UAH"), CurrencyVO("UAH"), CurrencyVO("USD")],
        )
        self.assertEqual(self.s.base.restore(posting), posting)

    def test_manual_results_with_same_total_but_different_allocation_are_rejected(
        self,
    ) -> None:
        """Полное ручное распределение 2+5 не подтверждает FIFO-назначение 3+4."""
        first = self.plan.plans[0]
        manual = tuple(
            layer.consume_from_issue(
                first.issue,
                quantity=QuantityVO(Decimal(q)),
                expected_version=0,
                updated_at=self.s.fx.at,
            )[1]
            for layer, q in ((self.s.a, "2"), (self.s.b, "5"))
        )
        results = (*manual, self.results[-1])
        self.s.base.create(
            posting=self.stock.snapshot(),
            consumptions=results,
            entry_bindings=self.bindings,
            positions=self.context["positions"],
            locations=self.context["locations"],
        )
        with self.assertRaises(ValuationPostingSourceError):
            self.create(consumptions=results)

    def test_missing_extra_or_duplicate_results_are_rejected(self) -> None:
        """Результаты покрывают ровно выбранные назначения, включая каждую часть многослойной группы."""
        extra = replace(
            self.results[0],
            layer=replace(self.results[0].layer, id=ValuationLayerIdVO(uuid4())),
        )
        for results in (
            (),
            self.results[:-1],
            (*self.results, self.results[0]),
            (*self.results, extra),
        ):
            with (
                self.subTest(count=len(results)),
                self.assertRaises(ValuationPostingSourceError),
            ):
                self.create(consumptions=results)

    def test_result_from_different_version_is_rejected_even_if_amount_matches(
        self,
    ) -> None:
        """Самосогласованная другая версия перехода не является результатом сохранённого назначения."""
        original = self.results[0]
        changed = replace(original, version_before=1, version_after=2)
        changed.ensure_valid()
        with self.assertRaises(ValuationPostingSourceError):
            self.create(consumptions=(changed, *self.results[1:]))

    def test_changed_before_quantity_with_same_version_and_cost_delta_is_rejected(
        self,
    ) -> None:
        """Одинаковое количество потребления и денежная дельта не скрывают другой исходный остаток."""
        candidate = self.plan.plans[0].candidates[1]
        layer = self.s.fx.v.restore(
            self.layer(candidate),
            remaining_qty=QuantityVO(Decimal(9)),
            remaining_cost=MoneyVO(Decimal(108), CurrencyVO("UAH")),
        )
        _, result = layer.consume_from_issue(
            self.plan.plans[0].issue,
            quantity=QuantityVO(Decimal(4)),
            expected_version=0,
            updated_at=self.s.fx.at,
        )
        self.assertEqual(result.cost, self.results[1].cost)
        with self.assertRaises(ValuationPostingSourceError):
            self.create(consumptions=(self.results[0], result, self.results[2]))

    def test_changed_before_update_or_initial_cost_basis_is_rejected(self) -> None:
        """Сверяется весь снимок кандидата, включая время и первоначальную стоимость, а не одна версия."""
        candidate = self.plan.plans[0].candidates[1]
        for changes in (
            dict(updated_at=candidate.updated_at + timedelta(minutes=1)),
            dict(
                cost_basis=CostBasisVO(
                    candidate.layer.cost_basis.quantity,
                    MoneyVO(Decimal(121), CurrencyVO("UAH")),
                ),
                remaining_cost=MoneyVO(Decimal(121), CurrencyVO("UAH")),
            ),
        ):
            layer = self.s.fx.v.restore(self.layer(candidate), **changes)
            _, result = layer.consume_from_issue(
                self.plan.plans[0].issue,
                quantity=QuantityVO(Decimal(4)),
                expected_version=0,
                updated_at=self.s.fx.at,
            )
            with self.assertRaises(ValuationPostingSourceError):
                self.create(consumptions=(self.results[0], result, self.results[2]))

    def test_current_posting_must_equal_full_saved_source_including_history(
        self,
    ) -> None:
        """Сохраняется точное основание, включая execution source и исторический коэффициент при тех же ID."""
        source = self.stock.snapshot()
        entry = source.entries[0]
        changed_conversion = replace(
            entry,
            conversion=QuantityConversionSnapshotVO(
                QuantityVO(Decimal(14)), entry.base_uom, Decimal(".5")
            ),
        )
        for current in (
            replace(source, source=PostingSourceVO(StockExecutionIdVO(uuid4()))),
            replace(source, posted_at=source.posted_at + timedelta(minutes=1)),
            replace(source, entries=(changed_conversion, source.entries[1])),
        ):
            current.ensure_valid()
            with self.assertRaises(ValuationPostingSourceError):
                self.create(posting=current)

    def test_registration_rechecks_physical_context_after_plan_validation(self) -> None:
        """Согласованные снимки другого владельца не подменяют реальный контекст исходной позиции."""
        first, second = self.plan.plans
        owner = StockOwnerIdVO(uuid4())
        forged = StockIssueFifoPlanSnapshot.create(
            issue=replace(first.issue, owner_id=owner),
            candidates=tuple(
                replace(c, layer=replace(c.layer, owner_id=owner))
                for c in first.candidates
            ),
        )
        plan = replace(self.plan, plans=(forged, second))
        plan.ensure_valid()
        with self.assertRaises(ValuationPostingSourceError):
            self.create(plan=plan, consumptions=self.apply(plan))

    def test_single_result_and_full_plan_are_revalidated_before_registration(
        self,
    ) -> None:
        """Фабрика заново проверяет планы и арифметику результата, даже если объекты имеют ожидаемый тип."""
        broken_plan = replace(self.plan, plans=tuple(reversed(self.plan.plans)))
        with self.assertRaises(InventoryError):
            self.create(plan=broken_plan)
        broken = replace(self.results[0], cost=MoneyVO(Decimal(29), CurrencyVO("UAH")))
        with self.assertRaises(InventoryError):
            self.create(consumptions=(broken, *self.results[1:]))

    def test_new_factory_requires_specialized_plan_source_and_results(self) -> None:
        """Полный контракт не заменяется одиночным планом, агрегатом или mutable коллекцией результатов."""
        for changes in (
            dict(plan=None),
            dict(plan=self.plan.plans[0]),
            dict(posting=self.stock),
            dict(consumptions=[*self.results]),
            dict(consumptions=(None,)),
        ):
            with (
                self.subTest(changes=changes),
                self.assertRaises(ValuationPostingSourceError),
            ):
                self.create(**changes)

    def test_existing_binding_and_registration_time_rules_are_preserved(self) -> None:
        """Делегирование прежнему расходному журналу сохраняет проверки привязок и времени после всех потреблений."""
        with self.assertRaises(ValuationPostingSourceError):
            self.create(entry_bindings=())
        with self.assertRaises(ValuationPostingTimeError):
            self.create(posted_at=self.s.fx.at - timedelta(seconds=1))
        self.assertEqual(self.create(posted_at=self.s.fx.at).posted_at, self.s.fx.at)

    def test_results_remain_registerable_after_unrelated_later_consumption(
        self,
    ) -> None:
        """Исторические результаты регистрируются без чтения новой версии слоя после другого расхода."""
        item = self.plan.plans[0]
        changed, _ = self.s.b.consume_fifo_allocation(item, updated_at=self.s.fx.at)
        later = self.s.fx.produce(self.s.fx.issue_for("1"))
        advanced, _ = changed.consume_from_issue(
            later, expected_version=1, updated_at=self.s.fx.at
        )
        self.assertEqual(advanced.version, 2)
        self.assertEqual(len(self.create().entries), 3)

    def test_planning_and_registration_do_not_mutate_sources_or_apply_stock(
        self,
    ) -> None:
        """Полная цепочка строит новые факты без изменения исходных слоёв и физических остатков."""
        source = self.stock.snapshot()
        self.create()
        self.assertEqual(self.stock.snapshot(), source)
        self.assertEqual((self.s.a.version, self.s.b.version), (0, 0))
        self.assertEqual(self.s.f.first.version, 0)
        with self.assertRaises(FrozenInstanceError):
            self.plan.plans = ()

    def test_serial_whole_posting_preserves_single_pcs_and_result(self) -> None:
        """Полный план сохраняет неделимость SERIAL и прежнюю проверку физического основания."""
        layer, position, stock, issue = self.s.serial_context()
        plan = stock.issue_fifo_plan(
            candidates=(layer.fifo_snapshot(),),
            positions=(position.snapshot(),),
            locations=(self.s.f.first_location,),
        )
        self.assertEqual(plan.plans[0].issue.serial_id, issue.serial_id)
        results = self.apply(plan)
        posting = self.create(
            plan=plan,
            posting=stock.snapshot(),
            consumptions=results,
            positions=(position.snapshot(),),
            locations=(self.s.f.first_location,),
            entry_bindings=(replace(self.bindings[0], layer_id=layer.id),),
        )
        self.assertEqual(posting.entries[0].quantity_delta.value, Decimal(-1))

    def test_hostile_decimal_context_preserves_full_chain(self) -> None:
        """Полное планирование, сверка состояний и журнал не теряют разряды во внешнем Decimal context."""
        with localcontext() as ctx:
            ctx.prec = 1
            ctx.traps[Inexact] = True
            ctx.traps[Rounded] = True
            plan = self.build()
            results = self.apply(plan)
            posting = self.create(plan=plan, consumptions=results)
        self.assertEqual(
            [entry.cost_delta.amount for entry in posting.entries],
            [Decimal(-30), Decimal(-48), Decimal(-20)],
        )


if __name__ == "__main__":
    unittest.main()
