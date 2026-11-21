"""Независимые группы целых Allocation и несколько Shipment одного склада."""

import unittest
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal
from uuid import uuid4

from test import test_inventory_fulfillment_replanning_domain as fixtures
from test import test_inventory_fulfillment_progress_domain as progress_fixtures
from src.modules.inventory.domain.error import InventoryError
from src.modules.inventory.domain.fulfillment_plan.aggregate import FulfillmentPlan
from src.modules.inventory.domain.fulfillment_plan.entity.fulfillment_allocation import (
    FulfillmentAllocation,
)
from src.modules.inventory.domain.fulfillment_plan.value_object.allocation_status import (
    FulfillmentAllocationStatus,
)
from src.modules.inventory.domain.fulfillment_plan.value_object.status import (
    FulfillmentPlanStatus,
)
from src.modules.inventory.domain.shipment.aggregate import Shipment
from src.modules.inventory.domain.shipment.entity.shipment_line import ShipmentLine
from src.modules.inventory.domain.shipment.value_object.fulfillment_line_binding import (
    FulfillmentShipmentLineBindingVO,
)
from src.modules.inventory.domain.shipment.value_object.identifier import ShipmentIdVO
from src.modules.inventory.domain.shipment.value_object.line_id import ShipmentLineIdVO
from src.modules.inventory.domain.value_object.quantity import QuantityVO
from src.modules.inventory.domain.inventory_item.value_object.identifier import (
    InventoryItemIdVO,
)


class FulfillmentShipmentGroupsDomainTests(unittest.TestCase):
    """Проверяет явный состав, неизменность назначенной группы и независимый прогресс одного склада."""

    def setUp(self) -> None:
        """Готовит две строки одного склада A: первая=3, вторая=4, обе подтверждены резервами."""
        self.f = fixtures.FulfillmentReplanningDomainTests()
        self.f.setUp()
        self.rf, self.pf = self.f.rf, self.f.pf
        self.first = self.pf.allocation
        self.second = self.pf.create_allocation(
            source_ref=self.pf.other_ref, quantity=QuantityVO(Decimal(4))
        )
        self.planned = self.pf.mark(self.pf.add(self.pf.one, self.second))
        self.reserve_a = self.rf.first_reservation
        self.reserve_b = self.rf.reserve(self.second)
        self.plan = self.rf.confirm(
            self.planned,
            bindings=(
                self.rf.first_binding,
                self.rf.binding(self.second, self.reserve_b),
            ),
            reservations=(
                self.reserve_a.fulfillment_snapshot(),
                self.reserve_b.fulfillment_snapshot(),
            ),
            warehouses=(self.pf.a,),
        )
        self.at = self.f.at
        self.work = progress_fixtures.FulfillmentProgressDomainTests()
        self.work.setUp()
        self.work.at = self.at
        self.a = self.draft((self.first,))
        self.b = self.draft((self.second,))

    def draft(
        self,
        rows: tuple[FulfillmentAllocation, ...],
        plan: FulfillmentPlan | None = None,
        **changes: object,
    ) -> Shipment:
        """Создаёт производный черновик с точным выбранным набором резервов и новых ID строк."""
        target = self.plan if plan is None else plan
        reserves = {self.first.id: self.reserve_a, self.second.id: self.reserve_b}
        return Shipment.create_from_fulfillment_plan(
            **(
                dict(
                    identifier=ShipmentIdVO(uuid4()),
                    fulfillment_plan=target.shipment_snapshot(),
                    warehouse=self.pf.a,
                    order=self.f.order,
                    inventory_items=(self.pf.item,),
                    reservations=tuple(
                        reserves[row.id].fulfillment_snapshot() for row in rows
                    ),
                    line_bindings=tuple(
                        FulfillmentShipmentLineBindingVO(
                            row.id, ShipmentLineIdVO(uuid4())
                        )
                        for row in rows
                    ),
                    created_at=self.at,
                )
                | changes
            )
        )

    def assign(
        self, draft: Shipment, plan: FulfillmentPlan | None = None, **changes: object
    ) -> FulfillmentPlan:
        """Назначает полный явный состав данного черновика в текущей версии плана."""
        target = self.plan if plan is None else plan
        return target.assign_shipment(
            draft.assignment_snapshot(),
            **(dict(expected_version=target.version, updated_at=self.at) | changes),
        )

    def confirm(
        self, draft: Shipment, plan: FulfillmentPlan, **changes: object
    ) -> Shipment:
        """Подтверждает по точным текущим резервам выбранной группы без резервов соседних Shipment."""
        reserves = {
            self.reserve_a.id: self.reserve_a,
            self.reserve_b.id: self.reserve_b,
        }
        return draft.confirm_from_fulfillment_plan(
            **(
                dict(
                    expected_version=draft.version,
                    fulfillment_plan=plan.shipment_snapshot(),
                    warehouse=self.pf.a,
                    order=self.f.order,
                    inventory_items=(self.pf.item,),
                    reservations=tuple(
                        reserves[line.reservation_id].fulfillment_snapshot()
                        for line in draft.lines
                    ),
                    updated_at=self.at,
                )
                | changes
            )
        )

    def register(self, plan: FulfillmentPlan, shipment: Shipment) -> FulfillmentPlan:
        """Регистрирует весь накопленный снимок конкретного Shipment по текущей версии корня."""
        return plan.register_shipment(
            shipment.fulfillment_snapshot(),
            expected_version=plan.version,
            updated_at=max(plan.updated_at, shipment.updated_at),
        )

    def started_a(self) -> tuple[FulfillmentPlan, Shipment]:
        """Назначает A и регистрирует 1 из 3, оставляя соседнюю группу свободной."""
        plan = self.assign(self.a)
        fact = self.work.execute(self.confirm(self.a, plan))
        return self.register(plan, fact), fact

    def test_factory_selects_one_whole_allocation(self) -> None:
        """Выбор одной строки не требует соседнюю строку того же склада."""
        self.assertEqual(len(self.a.lines), 1)
        self.assertEqual(self.a.lines[0].planned_qty, self.first.quantity)
        self.assertEqual(self.b.lines[0].planned_qty, self.second.quantity)
        self.assertEqual(self.a.warehouse_id, self.b.warehouse_id)

    def test_unselected_planned_allocation_does_not_block_factory(self) -> None:
        """Только выбранная Allocation обязана быть подтверждённой."""
        partial = self.rf.confirm(
            self.planned,
            bindings=(self.rf.first_binding,),
            reservations=(self.reserve_a.fulfillment_snapshot(),),
            warehouses=(self.pf.a,),
        )
        draft = self.draft((self.first,), partial)
        plan = self.assign(draft, partial)
        shipment = self.confirm(draft, plan)
        self.assertEqual(shipment.lines[0].fulfillment_allocation_id, self.first.id)
        self.assertEqual(
            plan.allocations[1].status, FulfillmentAllocationStatus.PLANNED
        )

    def test_unselected_item_snapshot_is_not_required(self) -> None:
        """Для другой товарной строки того же склада не запрашиваются её текущие справочники."""
        item_id = InventoryItemIdVO(uuid4())
        second = replace(self.plan.allocations[1], inventory_item_id=item_id)
        plan = self.f.restore(self.plan, allocations=(self.plan.allocations[0], second))
        order = replace(
            self.f.order,
            lines=tuple(
                (
                    replace(line, inventory_item_id=item_id)
                    if line.source_ref == self.second.source_ref
                    else line
                )
                for line in self.f.order.lines
            ),
        )
        draft = self.draft((self.first,), plan, order=order)
        self.assertEqual(len(draft.lines), 1)

    def test_reserve_scope_is_exact_selected_set(self) -> None:
        """Лишний резерв соседней группы отклоняется так же, как пропуск выбранного."""
        for reserves in (
            (),
            (
                self.reserve_a.fulfillment_snapshot(),
                self.reserve_b.fulfillment_snapshot(),
            ),
        ):
            with self.subTest(reserves=reserves), self.assertRaises(InventoryError):
                self.draft((self.first,), reservations=reserves)

    def test_two_groups_can_be_assigned_same_warehouse(self) -> None:
        """Два независимых Shipment сохраняют разные назначения и даты одного склада."""
        first = self.assign(self.a)
        both = self.assign(self.b, first, updated_at=self.at + timedelta(seconds=1))
        self.assertEqual(both.allocations[0].shipment_assignment.shipment_id, self.a.id)
        self.assertEqual(both.allocations[1].shipment_assignment.shipment_id, self.b.id)
        self.assertIs(both.allocations[0], first.allocations[0])
        both.shipment_snapshot().ensure_valid()
        self.f.restore(both)

    def test_b_can_be_built_and_confirmed_after_a_starts(self) -> None:
        """Погашение и прогресс A не мешают новому черновику B с его полным резервом."""
        plan, _ = self.started_a()
        draft = self.draft((self.second,), plan)
        assigned = self.assign(draft, plan)
        shipment = self.confirm(draft, assigned)
        self.assertEqual(shipment.lines[0].reservation_id, self.reserve_b.id)
        self.assertIs(assigned.allocations[0], plan.allocations[0])

    def test_independent_progress_one_then_four_then_two_finishes_plan(self) -> None:
        """A=1, B=4, A+=2 дают FULFILLED при независимых версиях и времени Shipment."""
        plan, a = self.started_a()
        plan = self.assign(self.b, plan)
        b = self.work.execute(
            self.confirm(self.b, plan),
            {self.b.lines[0].id: "4"},
            at=self.at + timedelta(seconds=1),
        )
        plan = self.register(plan, b)
        self.assertEqual(plan.status, FulfillmentPlanStatus.PARTIALLY_FULFILLED)
        self.assertEqual(
            tuple(row.fulfilled_qty.value for row in plan.allocations),
            (Decimal(1), Decimal(4)),
        )
        plan.shipment_snapshot().ensure_valid()
        a = self.work.execute(
            a, {a.lines[0].id: "2"}, at=self.at + timedelta(seconds=2)
        )
        complete = self.register(plan, a)
        self.assertEqual(complete.status, FulfillmentPlanStatus.FULFILLED)
        self.assertEqual(
            tuple(row.fulfilled_qty.value for row in complete.allocations),
            (Decimal(3), Decimal(4)),
        )
        self.assertIs(self.register(complete, a), complete)
        self.f.restore(complete)

    def test_assignment_repeat_preserves_original_group(self) -> None:
        """Повтор не меняет назначение A после независимого назначения B."""
        assigned = self.assign(self.b, self.assign(self.a))
        repeated = self.assign(
            self.a, assigned, updated_at=self.at + timedelta(minutes=1)
        )
        self.assertIs(repeated, assigned)

    def test_same_allocation_cannot_be_assigned_or_confirmed_by_competing_shipment(
        self,
    ) -> None:
        """Назначение одной группе блокирует конкурента, даже если оба черновика построены заранее."""
        competitor = self.draft((self.first,))
        assigned = self.assign(self.a)
        with self.assertRaises(InventoryError):
            self.assign(competitor, assigned)
        with self.assertRaises(InventoryError):
            self.confirm(competitor, assigned)
        with self.assertRaises(InventoryError):
            self.draft((self.first,), assigned)
        self.assertIsNone(assigned.allocations[1].shipment_assignment)

    def test_assigned_group_cannot_be_enlarged_under_same_shipment_id(self) -> None:
        """Повторное использование Shipment ID не добавляет соседнюю Allocation в назначенную группу."""
        assigned = self.assign(self.a)
        enlarged = self.draft((self.first, self.second), identifier=self.a.id)
        with self.assertRaises(InventoryError):
            self.assign(enlarged, assigned)
        self.assertIsNone(assigned.allocations[1].shipment_assignment)

    def test_assigned_group_cannot_be_shrunk_in_assignment_or_confirmation(
        self,
    ) -> None:
        """После назначения обеих строк их нельзя подменить поднабором того же Shipment."""
        group = self.draft((self.first, self.second))
        assigned = self.assign(group)
        truncated = replace(group, lines=(group.lines[0],))
        with self.assertRaises(InventoryError):
            self.assign(truncated, assigned)
        with self.assertRaises(InventoryError):
            self.confirm(truncated, assigned)

    def test_group_progress_requires_zero_rows_too(self) -> None:
        """Факт A=1 в группе A/B включает нулевую строку B; её пропуск отклоняется."""
        group = self.draft((self.first, self.second))
        assigned = self.assign(group)
        shipment = self.confirm(group, assigned)
        selected = next(
            line
            for line in shipment.lines
            if line.fulfillment_allocation_id == self.first.id
        )
        fact = self.work.execute(shipment, {selected.id: "1"})
        snapshot = fact.fulfillment_snapshot()
        positive = tuple(
            line for line in snapshot.lines if not line.shipped_qty.value.is_zero()
        )
        with self.assertRaises(InventoryError):
            assigned.register_shipment(
                replace(snapshot, lines=positive),
                expected_version=assigned.version,
                updated_at=self.at,
            )
        progressed = self.register(assigned, fact)
        self.assertTrue(
            all(row.shipment_progress is not None for row in progressed.allocations)
        )
        self.assertEqual(
            progressed.get_allocation(self.second.id).fulfilled_qty,
            QuantityVO(Decimal(0)),
        )

    def test_wrong_shipment_id_cannot_register_group_fact(self) -> None:
        """Полный входной снимок не определяет принадлежность группы: она берётся из назначений плана."""
        assigned = self.assign(self.a)
        fact = self.work.execute(self.confirm(self.a, assigned))
        with self.assertRaises(InventoryError):
            assigned.register_shipment(
                replace(fact.fulfillment_snapshot(), id=ShipmentIdVO(uuid4())),
                expected_version=assigned.version,
                updated_at=self.at,
            )

    def test_fact_cannot_include_allocation_of_another_group(self) -> None:
        """Строка соседнего Shipment не добавляется к факту выбранной группы."""
        assigned = self.assign(self.b, self.assign(self.a))
        a = self.work.execute(self.confirm(self.a, assigned))
        b = self.work.execute(self.confirm(self.b, assigned))
        enlarged = replace(
            a.fulfillment_snapshot(),
            lines=(*a.fulfillment_snapshot().lines, *b.fulfillment_snapshot().lines),
        )
        with self.assertRaises(InventoryError):
            assigned.register_shipment(
                enlarged, expected_version=assigned.version, updated_at=self.at
            )

    def test_release_one_group_keeps_other_assignment_and_progress(self) -> None:
        """Отмена B освобождает только B, когда A уже исполняется на том же складе."""
        assigned = self.assign(self.b, self.assign(self.a))
        a = self.work.execute(self.confirm(self.a, assigned))
        progressed = self.register(assigned, a)
        cancelled = self.b.cancel(expected_version=0, updated_at=self.at)
        result = progressed.release_shipment_assignment(
            cancelled.assignment_snapshot(),
            expected_version=progressed.version,
            updated_at=self.at,
        )
        self.assertIs(result.allocations[0], progressed.allocations[0])
        self.assertIsNone(result.allocations[1].shipment_assignment)
        self.assertEqual(result.status, FulfillmentPlanStatus.PARTIALLY_FULFILLED)
        self.assertIs(
            result.release_shipment_assignment(
                cancelled.assignment_snapshot(),
                expected_version=result.version,
                updated_at=self.at,
            ),
            result,
        )
        result.shipment_snapshot().ensure_valid()

    def test_release_requires_entire_assigned_group(self) -> None:
        """Отмена части двухстрочного черновика не снимает часть назначения."""
        group = self.draft((self.first, self.second))
        assigned = self.assign(group)
        cancelled = group.cancel(expected_version=0, updated_at=self.at)
        snapshot = cancelled.assignment_snapshot()
        with self.assertRaises(InventoryError):
            assigned.release_shipment_assignment(
                replace(snapshot, lines=(snapshot.lines[0],)),
                expected_version=assigned.version,
                updated_at=self.at,
            )
        self.assertTrue(
            all(row.shipment_assignment is not None for row in assigned.allocations)
        )

    def test_old_cancellation_cannot_release_new_group_assignment(self) -> None:
        """Снимок прежней отмены не снимает новое назначение B с другим Shipment ID."""
        assigned = self.assign(self.b)
        cancelled = self.b.cancel(expected_version=0, updated_at=self.at)
        released = assigned.release_shipment_assignment(
            cancelled.assignment_snapshot(),
            expected_version=assigned.version,
            updated_at=self.at,
        )
        new = self.draft((self.second,), released)
        reassigned = self.assign(new, released)
        with self.assertRaises(InventoryError):
            reassigned.release_shipment_assignment(
                cancelled.assignment_snapshot(),
                expected_version=reassigned.version,
                updated_at=self.at,
            )

    def test_restore_and_snapshot_require_consistent_metadata_inside_group(
        self,
    ) -> None:
        """Одна группа не смешивает версии, время, основания и ID строк назначения."""
        group = self.draft((self.first, self.second))
        assigned = self.assign(group)
        a, b = assigned.allocations
        variants = (
            replace(b.shipment_assignment, shipment_version=1),
            replace(b.shipment_assignment, assigned_at=self.at - timedelta(seconds=1)),
            replace(b.shipment_assignment, source_plan_version=0),
            replace(
                b.shipment_assignment,
                shipment_line_id=a.shipment_assignment.shipment_line_id,
            ),
        )
        for assignment in variants:
            row = replace(b, shipment_assignment=assignment)
            with self.subTest(assignment=assignment), self.assertRaises(InventoryError):
                self.f.restore(assigned, allocations=(a, row))
            snapshot = assigned.shipment_snapshot()
            with (
                self.subTest(snapshot_assignment=assignment),
                self.assertRaises(InventoryError),
            ):
                replace(
                    snapshot,
                    allocations=(
                        snapshot.allocations[0],
                        replace(
                            snapshot.allocations[1], shipment_assignment=assignment
                        ),
                    ),
                ).ensure_valid()

    def test_restore_rejects_same_shipment_id_on_different_warehouses(self) -> None:
        """Несколько групп одного склада допустимы, а одна группа разных складов запрещена."""
        group = self.draft((self.first, self.second))
        assigned = self.assign(group)
        row = replace(
            assigned.allocations[1],
            source=replace(self.second.source, warehouse_id=self.pf.b.id),
        )
        with self.assertRaises(InventoryError):
            self.f.restore(assigned, allocations=(assigned.allocations[0], row))
        snapshot = assigned.shipment_snapshot()
        with self.assertRaises(InventoryError):
            replace(
                snapshot,
                allocations=(
                    snapshot.allocations[0],
                    replace(snapshot.allocations[1], source=row.source),
                ),
            ).ensure_valid()

    def test_restore_and_snapshot_reject_partial_checkpoint_within_assigned_group(
        self,
    ) -> None:
        """Прогресс группы должен включать нулевые строки этой же группы, но не соседние Shipment."""
        group = self.draft((self.first, self.second))
        assigned = self.assign(group)
        shipment = self.confirm(group, assigned)
        line = next(
            line
            for line in shipment.lines
            if line.fulfillment_allocation_id == self.first.id
        )
        progressed = self.register(
            assigned, self.work.execute(shipment, {line.id: "1"})
        )
        row = replace(progressed.allocations[1], shipment_progress=None)
        with self.assertRaises(InventoryError):
            self.f.restore(progressed, allocations=(progressed.allocations[0], row))
        snapshot = progressed.shipment_snapshot()
        with self.assertRaises(InventoryError):
            replace(
                snapshot,
                allocations=(
                    snapshot.allocations[0],
                    replace(snapshot.allocations[1], shipment_progress=None),
                ),
            ).ensure_valid()

    def test_progress_metadata_is_consistent_per_group_not_per_warehouse(self) -> None:
        """Разные Shipment хранят разные версии/даты; одна группа не принимает смешанные checkpoint."""
        group = self.draft((self.first, self.second))
        assigned = self.assign(group)
        shipment = self.confirm(group, assigned)
        line = next(
            line
            for line in shipment.lines
            if line.fulfillment_allocation_id == self.first.id
        )
        progressed = self.register(
            assigned, self.work.execute(shipment, {line.id: "1"})
        )
        row = replace(
            progressed.allocations[1],
            shipment_progress=replace(
                progressed.allocations[1].shipment_progress, shipment_version=3
            ),
        )
        with self.assertRaises(InventoryError):
            self.f.restore(progressed, allocations=(progressed.allocations[0], row))
        snapshot = progressed.shipment_snapshot()
        with self.assertRaises(InventoryError):
            replace(
                snapshot,
                allocations=(
                    snapshot.allocations[0],
                    replace(
                        snapshot.allocations[1], shipment_progress=row.shipment_progress
                    ),
                ),
            ).ensure_valid()

    def test_replanning_free_neighbor_keeps_assigned_group_same_warehouse(self) -> None:
        """Не начатое B можно заменить новым B того же склада, не затрагивая назначенный A."""
        assigned = self.assign(self.a)
        closed = self.reserve_b.release_all(
            expected_version=self.reserve_b.version, updated_at=self.at
        )
        released = assigned.release_reservation_confirmations(
            bindings=(self.rf.binding(self.second, closed),),
            reservations=(closed.fulfillment_snapshot(),),
            expected_version=assigned.version,
            updated_at=self.at,
        )
        new = self.pf.create_allocation(
            source_ref=self.second.source_ref, quantity=self.second.quantity
        )
        replanned = released.replan_allocations(
            allocation_ids=(self.second.id,),
            replacements=(new,),
            demand=self.pf.demand,
            inventory_items=(self.pf.item,),
            warehouses=(self.pf.a,),
            expected_version=released.version,
            updated_at=self.at,
        )
        self.assertIs(replanned.allocations[0], assigned.allocations[0])
        self.assertEqual(
            replanned.allocations[1].status, FulfillmentAllocationStatus.CANCELLED
        )
        self.assertIsNone(replanned.allocations[2].shipment_assignment)
        replanned.shipment_snapshot().ensure_valid()

    def test_free_neighbor_cancellation_does_not_change_started_group(self) -> None:
        """Отмена намерения B на том же складе не снимает контрольную точку A."""
        plan, _ = self.started_a()
        closed = self.reserve_b.release_all(
            expected_version=self.reserve_b.version, updated_at=self.at
        )
        released = plan.release_reservation_confirmations(
            bindings=(self.rf.binding(self.second, closed),),
            reservations=(closed.fulfillment_snapshot(),),
            expected_version=plan.version,
            updated_at=self.at,
        )
        cancelled = released.cancel_allocations(
            allocation_ids=(self.second.id,),
            expected_version=released.version,
            updated_at=self.at,
        )
        self.assertIs(cancelled.allocations[0], plan.allocations[0])
        self.assertEqual(cancelled.status, FulfillmentPlanStatus.PARTIALLY_FULFILLED)
        cancelled.shipment_snapshot().ensure_valid()

    def test_partial_quantity_of_one_allocation_is_not_allowed(self) -> None:
        """Выбор поднабора строк не разрешает дробить количество одной Allocation между отправлениями."""
        line = ShipmentLine.create(
            identifier=self.a.lines[0].id,
            inventory_item=self.pf.item,
            reservation=self.reserve_a.shipment_snapshot(),
            quantity=QuantityVO(Decimal(2)),
            uom=self.first.base_uom,
            fulfillment_allocation_id=self.first.id,
        )
        partial = replace(self.a, lines=(line,))
        with self.assertRaises(InventoryError):
            self.assign(partial)
        assigned = self.assign(self.a)
        with self.assertRaises(InventoryError):
            self.confirm(partial, assigned)

    def test_unknown_foreign_and_cancelled_selection_is_rejected(self) -> None:
        """Явный выбор остаётся непустым, типизированным и ограниченным действующими Allocation своего склада."""
        with self.assertRaises(InventoryError):
            self.draft((self.first,), line_bindings=())
        with self.assertRaises(InventoryError):
            self.draft((self.first,), warehouse=self.pf.b)
        with self.assertRaises(InventoryError):
            self.draft(
                (self.first,),
                line_bindings=(
                    FulfillmentShipmentLineBindingVO(
                        self.rf.second.id, ShipmentLineIdVO(uuid4())
                    ),
                ),
            )
        closed = self.reserve_b.release_all(expected_version=1, updated_at=self.at)
        released = self.plan.release_reservation_confirmations(
            bindings=(self.rf.binding(self.second, closed),),
            reservations=(closed.fulfillment_snapshot(),),
            expected_version=self.plan.version,
            updated_at=self.at,
        )
        cancelled = released.cancel_allocations(
            allocation_ids=(self.second.id,),
            expected_version=released.version,
            updated_at=self.at,
        )
        with self.assertRaises(InventoryError):
            self.draft((self.second,), cancelled)


if __name__ == "__main__":
    unittest.main()
