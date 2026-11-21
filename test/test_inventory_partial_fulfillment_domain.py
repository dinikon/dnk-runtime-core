"""Отгрузка готового склада и подтверждение оставшихся резервов после начала исполнения плана."""

import unittest
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal, Inexact, Rounded, localcontext
from uuid import uuid4

from test import test_inventory_fulfillment_progress_domain as progress_fixture
from src.modules.inventory.domain.error import InventoryError, QuantityStepError
from src.modules.inventory.domain.fulfillment_plan.aggregate import FulfillmentPlan
from src.modules.inventory.domain.fulfillment_plan.demand_snapshot import (
    FulfillmentDemandSnapshot,
)
from src.modules.inventory.domain.fulfillment_plan.error import (
    FulfillmentDemandExceededError,
    FulfillmentPlanContextError,
    FulfillmentPlanStatusError,
    FulfillmentPlanTimeError,
    FulfillmentPlanVersionConflictError,
    FulfillmentReservationConflictError,
    FulfillmentReservationUnavailableError,
    FulfillmentReservationVersionConflictError,
    FulfillmentShipmentProgressMismatchError,
    InvalidFulfillmentPlanValueError,
)
from src.modules.inventory.domain.fulfillment_plan.value_object.allocation_status import (
    FulfillmentAllocationStatus,
)
from src.modules.inventory.domain.fulfillment_plan.value_object.reservation_binding import (
    FulfillmentReservationBindingVO,
)
from src.modules.inventory.domain.fulfillment_plan.value_object.status import (
    FulfillmentPlanStatus,
)
from src.modules.inventory.domain.shipment.error import (
    ShipmentFulfillmentMismatchError,
)
from src.modules.inventory.domain.shipment.value_object.fulfillment_line_binding import (
    FulfillmentShipmentLineBindingVO,
)
from src.modules.inventory.domain.shipment.value_object.line_id import ShipmentLineIdVO
from src.modules.inventory.domain.shipment.value_object.status import ShipmentStatus
from src.modules.inventory.domain.stock_reservation.value_object.status import (
    StockReservationStatus,
)
from src.modules.inventory.domain.value_object.quantity import QuantityVO
from src.modules.inventory.domain.value_object.quantity_rules import QuantityRulesVO
from src.modules.inventory.domain.value_object.uom_code import UomCodeVO
from src.modules.inventory.domain.warehouse.error import WarehouseInactiveError
from src.modules.inventory.domain.warehouse.snapshot import WarehouseSnapshot
from src.modules.inventory.domain.warehouse.value_object.identifier import WarehouseIdVO


class PartialFulfillmentDomainTests(unittest.TestCase):
    """Проверяет смешанное подтверждение/исполнение без изменения чужих агрегатов и ослабления проверок готового склада."""

    def setUp(self) -> None:
        """Готовит A=3 CONFIRMED, B=4 PLANNED и Shipment A, созданный из частичного плана."""
        self.f = progress_fixture.FulfillmentProgressDomainTests()
        self.f.setUp()
        self.sf, self.rf, self.pf = self.f.f, self.f.rf, self.f.pf
        self.plan = self.rf.partial()
        self.at = self.f.at
        self.draft_a = self.sf.create(fulfillment_plan=self.plan.shipment_snapshot())
        self.plan, self.a = self.sf.assign_and_confirm(self.plan, self.draft_a)
        self.a1 = self.f.execute(self.a)

    def register_a(self, **changes: object) -> FulfillmentPlan:
        """Регистрирует положительный факт A, сохраняя неподтверждённый B."""
        return self.f.register(self.plan, self.a1, **changes)

    def demand(self, remaining: str = "6") -> FulfillmentDemandSnapshot:
        """Передаёт актуальный внешний остаток общей строки заказа без повторного вычитания отгруженного."""
        return replace(
            self.pf.demand,
            lines=tuple(
                (
                    replace(row, remaining_qty=QuantityVO(Decimal(remaining)))
                    if row.source_ref == self.pf.line_ref
                    else row
                )
                for row in self.pf.demand.lines
            ),
        )

    def confirm_b(self, plan: FulfillmentPlan, **changes: object) -> FulfillmentPlan:
        """Назначает B полный резерв по свежему спросу и контексту только ещё не начатого склада."""
        return plan.confirm_reservations(
            **(
                dict(
                    bindings=(self.rf.second_binding,),
                    reservations=(self.f.b_reservation,),
                    demand=self.demand(),
                    inventory_items=(self.pf.item,),
                    warehouses=(self.pf.b,),
                    expected_version=plan.version,
                    updated_at=max(self.at, plan.updated_at),
                )
                | changes
            )
        )

    def confirm_b_before_execution(self) -> FulfillmentPlan:
        """Пока A ещё не зарегистрирован, его полный неизменный резерв и текущий склад также обязательны."""
        return self.confirm_b(
            self.plan,
            demand=self.pf.demand,
            reservations=(self.sf.reservation, self.f.b_reservation),
            warehouses=(self.pf.a, self.pf.b),
        )

    def test_partial_plan_snapshot_contains_pending_rows_and_only_ready_warehouse_ships(
        self,
    ) -> None:
        """A строится и подтверждается без резервов B, а весь состав B остаётся PLANNED/None."""
        snapshot = self.plan.shipment_snapshot()
        pending = next(
            row for row in snapshot.allocations if row.id == self.rf.second.id
        )
        self.assertIsNone(pending.reservation)
        self.assertEqual(pending.status, FulfillmentAllocationStatus.PLANNED)
        self.assertEqual(self.a.status, ShipmentStatus.CONFIRMED)
        self.assertEqual(self.a.lines[0].planned_qty.value, Decimal(3))
        with self.assertRaises(ShipmentFulfillmentMismatchError):
            self.sf.create(
                fulfillment_plan=snapshot,
                warehouse=self.pf.b,
                reservations=(self.f.b_reservation,),
                line_bindings=(
                    FulfillmentShipmentLineBindingVO(
                        pending.id, ShipmentLineIdVO(uuid4())
                    ),
                ),
            )

    def test_register_a_keeps_b_planned_and_confirmation_coverage_false(self) -> None:
        """Первый факт создаёт PARTIALLY_FULFILLED без требования подтвердить весь план."""
        updated = self.register_a()
        self.assertEqual(updated.status, FulfillmentPlanStatus.PARTIALLY_FULFILLED)
        self.assertEqual(updated.version, self.plan.version + 1)
        self.assertFalse(updated.is_fully_confirmed())
        b = updated.get_allocation(self.rf.second.id)
        self.assertEqual(b.status, FulfillmentAllocationStatus.PLANNED)
        self.assertIsNone(b.reservation)
        self.assertIsNone(b.shipment_progress)
        self.assertEqual(b.fulfilled_qty.value, Decimal(0))
        updated.shipment_snapshot().ensure_valid()
        self.assertEqual(self.f.restore(updated), updated)

    def test_confirmation_coverage_is_derived_and_historical(self) -> None:
        """Пустой/плановый/частичный план не полностью подтверждён, а факт исполнения не отменяет исторические подтверждения."""
        for plan in (self.pf.draft, self.rf.plan, self.plan, self.register_a()):
            self.assertFalse(plan.is_fully_confirmed())
        after_b = self.confirm_b(self.register_a())
        self.assertTrue(after_b.is_fully_confirmed())
        self.assertEqual(after_b.status, FulfillmentPlanStatus.PARTIALLY_FULFILLED)
        self.assertNotIn("is_fully_confirmed", after_b.__dataclass_fields__)
        self.assertTrue(self.confirm_b_before_execution().is_fully_confirmed())

    def test_consumed_a_does_not_block_b_and_progress_is_preserved(self) -> None:
        """После погашения A подтверждение B не требует его текущий снимок и не меняет первый confirmed_at или прогресс."""
        after_a = self.register_a()
        consumed = self.rf.first_reservation.consume(
            QuantityVO(Decimal(1)),
            expected_version=self.rf.first_reservation.version,
            inventory_item=self.pf.item,
            consumed_at=self.at,
            updated_at=self.at,
        )
        self.assertEqual(consumed.status, StockReservationStatus.PARTIALLY_CONSUMED)
        original_a = after_a.get_allocation(self.pf.allocation.id)
        after_b = self.confirm_b(after_a)
        self.assertEqual(after_b.version, after_a.version + 1)
        self.assertEqual(after_b.get_allocation(original_a.id), original_a)
        self.assertEqual(
            after_b.get_allocation(self.rf.second.id).reservation.reservation_id,
            self.rf.second_reservation.id,
        )
        self.assertEqual(
            after_b.get_allocation(self.rf.second.id).fulfilled_qty.value, Decimal(0)
        )
        self.assertEqual(
            self.rf.second_reservation.fulfillment_snapshot(), self.f.b_reservation
        )

    def test_end_to_end_partial_plan_a_then_b_reaches_fulfilled(self) -> None:
        """A отгружается до резервирования B; затем остаток A и весь B завершают план без регрессии статуса."""
        after_a = self.register_a()
        covered = self.confirm_b(after_a)
        self.assertEqual(covered.status, FulfillmentPlanStatus.PARTIALLY_FULFILLED)
        draft_b = self.sf.create(
            fulfillment_plan=covered.shipment_snapshot(),
            warehouse=self.pf.b,
            reservations=(self.f.b_reservation,),
            created_at=self.at,
            line_bindings=(
                FulfillmentShipmentLineBindingVO(
                    self.rf.second.id, ShipmentLineIdVO(uuid4())
                ),
            ),
        )
        covered, b = self.sf.assign_and_confirm(
            covered,
            draft_b,
            warehouse=self.pf.b,
            reservations=(self.f.b_reservation,),
            updated_at=self.at,
        )
        full_a = self.f.execute(
            self.a1, {self.a.lines[0].id: "2"}, at=self.at + timedelta(minutes=1)
        )
        after_full_a = self.f.register(covered, full_a)
        full_b = self.f.execute(
            b, {b.lines[0].id: "4"}, at=self.at + timedelta(minutes=2)
        )
        completed = self.f.register(after_full_a, full_b)
        self.assertEqual(completed.status, FulfillmentPlanStatus.FULFILLED)
        self.assertTrue(completed.is_fully_confirmed())
        self.assertIs(self.f.register(completed, full_a), completed)
        self.assertIs(self.f.register(completed, full_b), completed)

    def test_b_confirmation_before_old_a_draft_confirmation_preserves_source(
        self,
    ) -> None:
        """Подтверждение другого склада увеличивает версию плана, но прежний черновик A сохраняет совместимое основание."""
        covered = self.confirm_b_before_execution()
        self.assertEqual(covered.status, FulfillmentPlanStatus.CONFIRMED)
        covered, a = self.sf.assign_and_confirm(
            covered,
            self.draft_a,
            updated_at=self.at,
        )
        self.assertEqual(a.fulfillment_source, self.draft_a.fulfillment_source)
        self.assertLess(a.fulfillment_source.plan_version, covered.version)
        snapshot = self.f.execute(a).fulfillment_snapshot()
        updated = covered.register_shipment(
            snapshot, expected_version=covered.version, updated_at=self.at
        )
        self.assertEqual(updated.status, FulfillmentPlanStatus.PARTIALLY_FULFILLED)

    def test_b_confirmation_after_a_confirm_but_before_a_execution_is_compatible(
        self,
    ) -> None:
        """Первый факт уже подтверждённого A принимается и после подтверждения B без замены исторической версии."""
        covered = self.confirm_b_before_execution()
        updated = self.f.register(covered, self.a1)
        self.assertEqual(
            updated.get_allocation(self.pf.allocation.id).fulfilled_qty.value,
            Decimal(1),
        )
        self.assertEqual(self.a1.fulfillment_source, self.a.fulfillment_source)

    def test_zero_row_of_started_shipment_needs_no_reservation_recheck(self) -> None:
        """Нулевая строка A с контрольной точкой исключается из текущих удержаний вместе с положительной строкой."""
        extra = self.pf.create_allocation(
            source_ref=self.pf.other_ref, quantity=QuantityVO(Decimal(2))
        )
        planned = self.pf.mark(
            self.pf.add(self.pf.add(self.pf.one, extra), self.rf.second)
        )
        third = self.rf.reserve(extra)
        partial = self.rf.confirm(
            planned,
            bindings=(self.rf.first_binding, self.rf.binding(extra, third)),
            reservations=(self.sf.reservation, third.fulfillment_snapshot()),
        )
        draft = self.sf.create(
            fulfillment_plan=partial.shipment_snapshot(),
            reservations=(self.sf.reservation, third.fulfillment_snapshot()),
            line_bindings=(
                self.sf.binding,
                FulfillmentShipmentLineBindingVO(extra.id, ShipmentLineIdVO(uuid4())),
            ),
        )
        partial, shipment = self.sf.assign_and_confirm(
            partial,
            draft,
            reservations=(self.sf.reservation, third.fulfillment_snapshot()),
        )
        fact = self.f.execute(shipment, {self.sf.binding.shipment_line_id: "1"})
        after_a = self.f.register(partial, fact)
        zero = after_a.get_allocation(extra.id)
        self.assertEqual(zero.fulfilled_qty.value, Decimal(0))
        self.assertIsNotNone(zero.shipment_progress)
        covered = self.confirm_b(after_a)
        self.assertTrue(covered.is_fully_confirmed())
        self.assertEqual(covered.get_allocation(extra.id), zero)

    def test_mixed_started_a_unstarted_confirmed_c_and_new_b_recheck_c(self) -> None:
        """Начатый A исключён, но прежний ещё не начатый C остаётся обязательным контекстом и полным удержанием."""
        warehouse_c = WarehouseSnapshot(WarehouseIdVO(uuid4()), True, None)
        allocation_c = self.pf.create_allocation(
            source=replace(self.pf.source, warehouse_id=warehouse_c.id),
            source_ref=self.pf.other_ref,
            quantity=QuantityVO(Decimal(1)),
        )
        draft = self.pf.add(self.pf.one, self.rf.second)
        draft = draft.add_allocation(
            allocation_c,
            demand=self.pf.demand,
            inventory_item=self.pf.item,
            warehouse=warehouse_c,
            expected_version=draft.version,
            updated_at=draft.updated_at,
        )
        planned = draft.mark_planned(
            demand=self.pf.demand,
            inventory_items=(self.pf.item,),
            warehouses=(self.pf.a, self.pf.b, warehouse_c),
            expected_version=draft.version,
            updated_at=self.rf.plan.updated_at,
        )
        partial = self.rf.confirm(
            planned,
            bindings=(self.rf.first_binding,),
            reservations=(self.sf.reservation,),
            warehouses=(self.pf.a, self.pf.b, warehouse_c),
        )
        self.assertEqual(
            sum(
                row.reservation is None
                for row in partial.shipment_snapshot().allocations
            ),
            2,
        )
        reserve_c = self.rf.reserve(allocation_c)
        with_c = partial.confirm_reservations(
            bindings=(self.rf.binding(allocation_c, reserve_c),),
            reservations=(self.sf.reservation, reserve_c.fulfillment_snapshot()),
            demand=self.pf.demand,
            inventory_items=(self.pf.item,),
            warehouses=(self.pf.a, self.pf.b, warehouse_c),
            expected_version=partial.version,
            updated_at=partial.updated_at,
        )
        with_c, shipment = self.sf.assign_and_confirm(
            with_c,
            self.sf.create(fulfillment_plan=with_c.shipment_snapshot()),
        )
        after_a = self.f.register(with_c, self.f.execute(shipment))
        context = dict(warehouses=(self.pf.b, warehouse_c))
        with self.assertRaises(FulfillmentPlanContextError):
            self.confirm_b(after_a, **context)
        with self.assertRaises(FulfillmentReservationVersionConflictError):
            self.confirm_b(
                after_a,
                **context,
                reservations=(
                    self.f.b_reservation,
                    replace(
                        reserve_c.fulfillment_snapshot(), version=reserve_c.version + 1
                    ),
                ),
            )
        covered = self.confirm_b(
            after_a,
            **context,
            reservations=(self.f.b_reservation, reserve_c.fulfillment_snapshot()),
        )
        self.assertTrue(covered.is_fully_confirmed())
        self.assertEqual(
            covered.get_allocation(allocation_c.id),
            after_a.get_allocation(allocation_c.id),
        )

    def test_exact_reservation_set_excludes_registered_a(self) -> None:
        """Лишний снимок начатого A, пропуск B и повтор B отклоняются вместо скрытого игнорирования входов."""
        after_a = self.register_a()
        for reservations, error in (
            ((), FulfillmentPlanContextError),
            ((self.sf.reservation, self.f.b_reservation), FulfillmentPlanContextError),
            (
                (self.f.b_reservation, self.f.b_reservation),
                FulfillmentReservationConflictError,
            ),
            ((self.sf.reservation,), FulfillmentPlanContextError),
        ):
            with (
                self.subTest(reservations=reservations),
                self.assertRaises(error),
            ):
                self.confirm_b(after_a, reservations=reservations)

    def test_not_started_a_still_requires_current_full_reservation(self) -> None:
        """Без зарегистрированного факта A его прежний полный резерв остаётся обязательным для подтверждения B."""
        with self.assertRaises(FulfillmentPlanContextError):
            self.confirm_b(
                self.plan, demand=self.pf.demand, warehouses=(self.pf.a, self.pf.b)
            )
        changed = replace(self.sf.reservation, version=self.sf.reservation.version + 1)
        with self.assertRaises(FulfillmentReservationVersionConflictError):
            self.confirm_b(
                self.plan,
                demand=self.pf.demand,
                warehouses=(self.pf.a, self.pf.b),
                reservations=(changed, self.f.b_reservation),
            )
        with self.assertRaises(FulfillmentReservationUnavailableError):
            self.confirm_b(
                self.plan,
                demand=self.pf.demand,
                warehouses=(self.pf.a, self.pf.b),
                reservations=(self.sf.reservation, self.f.b_reservation),
                updated_at=self.sf.reservation.expires_at,
            )

    def test_started_reservation_id_remains_unavailable_for_new_binding(self) -> None:
        """Исторический ID A остаётся занят в плане, даже когда текущий снимок A исключён из проверки удержаний."""
        after_a = self.register_a()
        binding = FulfillmentReservationBindingVO(
            self.rf.second.id,
            self.rf.first_reservation.id,
            self.rf.first_reservation.version,
        )
        with self.assertRaises(FulfillmentReservationConflictError):
            self.confirm_b(after_a, bindings=(binding,))
        with self.assertRaises(FulfillmentReservationConflictError):
            self.confirm_b(
                after_a, bindings=(self.rf.second_binding, self.rf.second_binding)
            )

    def test_started_allocation_cannot_be_rebound_and_other_reservations_stay_unchanged(
        self,
    ) -> None:
        """Подтверждение не переписывает начатую Allocation и не создаёт новые удержания."""
        after_a = self.register_a()
        with self.assertRaises(FulfillmentReservationConflictError):
            self.confirm_b(after_a, bindings=(self.rf.first_binding,))
        before = (self.rf.first_reservation, self.rf.second_reservation, after_a)
        with self.assertRaises(FulfillmentReservationVersionConflictError):
            self.confirm_b(
                after_a,
                reservations=(
                    replace(
                        self.f.b_reservation, version=self.f.b_reservation.version + 1
                    ),
                ),
            )
        self.assertEqual(
            before, (self.rf.first_reservation, self.rf.second_reservation, after_a)
        )

    def test_only_not_started_items_and_warehouses_form_current_context(self) -> None:
        """Новый шаг 2 подходит B=4, а историческое A=3 повторно не проверяется; лишний склад A запрещён."""
        after_a = self.register_a()
        item = replace(self.pf.item, quantity_rules=QuantityRulesVO(Decimal(2)))
        self.confirm_b(after_a, inventory_items=(item,))
        for changes in (
            dict(warehouses=(self.pf.a, self.pf.b)),
            dict(warehouses=()),
            dict(inventory_items=()),
            dict(inventory_items=(self.pf.item, self.pf.item)),
        ):
            with (
                self.subTest(changes=changes),
                self.assertRaises(FulfillmentPlanContextError),
            ):
                self.confirm_b(after_a, **changes)

    def test_new_b_still_requires_active_warehouse_and_current_quantity_rules(
        self,
    ) -> None:
        """Начатый A не ослабляет проверку нового количества и активного склада B."""
        after_a = self.register_a()
        with self.assertRaises(WarehouseInactiveError):
            self.confirm_b(after_a, warehouses=(replace(self.pf.b, is_active=False),))
        with self.assertRaises(QuantityStepError):
            self.confirm_b(
                after_a,
                inventory_items=(
                    replace(self.pf.item, quantity_rules=QuantityRulesVO(Decimal(3))),
                ),
            )

    def test_new_b_still_requires_full_unexpired_reservation_and_exact_version(
        self,
    ) -> None:
        """Неполный/закрытый/истёкший B и устаревшая выбранная версия не принимаются."""
        after_a = self.register_a()
        for snapshot in (
            replace(
                self.f.b_reservation,
                reserved_qty=QuantityVO(Decimal(3)),
                status=StockReservationStatus.PARTIALLY_RESERVED,
            ),
            replace(
                self.f.b_reservation,
                reserved_qty=QuantityVO(Decimal(0)),
                status=StockReservationStatus.RELEASED,
            ),
            replace(self.f.b_reservation, expires_at=self.at),
        ):
            with (
                self.subTest(snapshot=snapshot),
                self.assertRaises(FulfillmentReservationUnavailableError),
            ):
                self.confirm_b(after_a, reservations=(snapshot,))
        with self.assertRaises(FulfillmentReservationVersionConflictError):
            self.confirm_b(
                after_a,
                reservations=(
                    replace(
                        self.f.b_reservation, version=self.f.b_reservation.version + 1
                    ),
                ),
            )

    def test_remaining_demand_covers_only_unfulfilled_obligations(self) -> None:
        """После A=1 текущие 6 покрывают A=2/B=4; уменьшение до 5 отклоняется до закрепления B."""
        after_a = self.register_a()
        self.assertEqual(
            after_a.remaining_to_allocate(self.pf.line_ref, demand=self.demand()).value,
            Decimal(0),
        )
        with self.assertRaises(FulfillmentDemandExceededError):
            self.confirm_b(after_a, demand=self.demand("5"))
        covered = self.confirm_b(after_a)
        self.assertEqual(
            covered.remaining_to_allocate(self.pf.line_ref, demand=self.demand()).value,
            Decimal(0),
        )

    def test_completed_a_does_not_require_order_line_or_current_warehouse_context(
        self,
    ) -> None:
        """Полностью исполненная строка A может отсутствовать в текущей потребности подтверждаемого B."""
        b_allocation = self.pf.create_allocation(
            source=self.rf.second.source,
            source_ref=self.pf.other_ref,
            quantity=QuantityVO(Decimal(4)),
        )
        planned = self.pf.mark(self.pf.add(self.pf.one, b_allocation))
        b_res = self.rf.reserve(b_allocation)
        partial = self.rf.confirm(
            planned,
            bindings=(self.rf.first_binding,),
            reservations=(self.sf.reservation,),
        )
        draft = self.sf.create(fulfillment_plan=partial.shipment_snapshot())
        partial, a = self.sf.assign_and_confirm(partial, draft)
        full_a = self.f.execute(a, {a.lines[0].id: "3"})
        after_a = self.f.register(partial, full_a)
        demand = replace(self.pf.demand, lines=(self.pf.other_demand,))
        covered = after_a.confirm_reservations(
            bindings=(self.rf.binding(b_allocation, b_res),),
            reservations=(b_res.fulfillment_snapshot(),),
            demand=demand,
            inventory_items=(
                replace(self.pf.item, quantity_rules=QuantityRulesVO(Decimal(2))),
            ),
            warehouses=(self.pf.b,),
            expected_version=after_a.version,
            updated_at=self.at,
        )
        self.assertTrue(covered.is_fully_confirmed())
        self.assertEqual(covered.status, FulfillmentPlanStatus.PARTIALLY_FULFILLED)

    def test_same_warehouse_can_ship_selected_confirmed_subset(self) -> None:
        """Подтверждённая выбранная Allocation может отгружаться, пока соседняя строка склада остаётся PLANNED."""
        pending = self.pf.create_allocation(
            source_ref=self.pf.other_ref, quantity=QuantityVO(Decimal(2))
        )
        planned = self.pf.mark(self.pf.add(self.pf.one, pending))
        partial = self.rf.confirm(
            planned,
            bindings=(self.rf.first_binding,),
            reservations=(self.sf.reservation,),
            warehouses=(self.pf.a,),
        )
        draft = self.sf.create(fulfillment_plan=partial.shipment_snapshot())
        assigned, shipment = self.sf.assign_and_confirm(partial, draft)
        fact = self.f.execute(shipment, at=self.at)
        progressed = assigned.register_shipment(
            fact.fulfillment_snapshot(),
            expected_version=assigned.version,
            updated_at=self.at,
        )
        self.assertEqual(
            progressed.get_allocation(pending.id).status,
            FulfillmentAllocationStatus.PLANNED,
        )
        progressed.shipment_snapshot().ensure_valid()
        with self.assertRaises(FulfillmentShipmentProgressMismatchError):
            self.f.register(partial, self.a1)

    def test_existing_warehouse_cannot_be_shipped_twice_after_b_confirmation(
        self,
    ) -> None:
        """Подтверждение B не освобождает начатый A для нового назначения."""
        covered = self.confirm_b(self.register_a())
        with self.assertRaises(ShipmentFulfillmentMismatchError):
            self.sf.create(
                fulfillment_plan=covered.shipment_snapshot(), created_at=self.at
            )

    def test_restore_and_snapshot_enforce_mixed_state_matrix(self) -> None:
        """Смешанный прогресс восстанавливается, но CONFIRMED/PARTIALLY_CONFIRMED/FULFILLED не подменяют его статус."""
        after_a = self.register_a()
        self.assertEqual(self.f.restore(after_a), after_a)
        for status in (
            FulfillmentPlanStatus.CONFIRMED,
            FulfillmentPlanStatus.PARTIALLY_CONFIRMED,
            FulfillmentPlanStatus.FULFILLED,
        ):
            with (
                self.subTest(status=status),
                self.assertRaises(InvalidFulfillmentPlanValueError),
            ):
                self.f.restore(after_a, status=status)
        snapshot = self.plan.shipment_snapshot()
        pending = next(row for row in snapshot.allocations if row.reservation is None)
        for changed in (
            replace(snapshot, status=FulfillmentPlanStatus.CONFIRMED),
            replace(snapshot, status=FulfillmentPlanStatus.PARTIALLY_FULFILLED),
            replace(snapshot, allocations=(pending,)),
        ):
            with self.subTest(snapshot=changed), self.assertRaises(InventoryError):
                changed.ensure_valid()
        with self.assertRaises(InventoryError):
            replace(
                pending, status=FulfillmentAllocationStatus.CONFIRMED
            ).ensure_valid()

    def test_exact_replay_does_not_change_partial_confirmation_coverage(self) -> None:
        """Повтор A до подтверждения B не добавляет версию и не превращает план в полностью подтверждённый."""
        after_a = self.register_a()
        replay = self.f.register(
            after_a, self.a1, updated_at=self.at + timedelta(minutes=1)
        )
        self.assertIs(replay, after_a)
        self.assertFalse(replay.is_fully_confirmed())
        covered = self.confirm_b(after_a)
        self.assertIs(self.f.register(covered, self.a1), covered)

    def test_historical_source_keeps_scope_quantity_and_future_version_guards(
        self,
    ) -> None:
        """Историческое основание не разрешает будущую версию, смену количества или необеспеченный выбранный склад."""
        covered = self.confirm_b_before_execution()
        future = self.sf.restore(
            self.draft_a,
            fulfillment_source=replace(
                self.draft_a.fulfillment_source, plan_version=covered.version + 1
            ),
        )
        with self.assertRaises(InventoryError):
            self.sf.confirm(
                future, fulfillment_plan=covered.shipment_snapshot(), updated_at=self.at
            )
        snapshot = covered.shipment_snapshot()
        changed = replace(
            snapshot,
            allocations=tuple(
                (
                    replace(row, quantity=QuantityVO(Decimal(4)))
                    if row.id == self.pf.allocation.id
                    else row
                )
                for row in snapshot.allocations
            ),
        )
        with self.assertRaises(ShipmentFulfillmentMismatchError):
            self.sf.confirm(self.draft_a, fulfillment_plan=changed, updated_at=self.at)

    def test_strict_expected_version_time_and_inactive_lifecycle_guards_remain(
        self,
    ) -> None:
        """Доподтверждение всё ещё требует точную версию корня и неубывающее время; начатый план нельзя редактировать или отменить."""
        after_a = self.register_a()
        with self.assertRaises(FulfillmentPlanVersionConflictError):
            self.confirm_b(after_a, expected_version=after_a.version - 1)
        with self.assertRaises(InventoryError):
            self.confirm_b(after_a, expected_version=True)
        with self.assertRaises(FulfillmentPlanTimeError):
            self.confirm_b(
                after_a, updated_at=after_a.updated_at - timedelta(microseconds=1)
            )
        with self.assertRaises(FulfillmentPlanStatusError):
            after_a.cancel(expected_version=after_a.version, updated_at=self.at)
        with self.assertRaises(FulfillmentPlanStatusError):
            after_a.remove_allocation(
                self.rf.second.id, expected_version=after_a.version, updated_at=self.at
            )

    def test_fractional_partial_execution_then_confirmation_is_exact(self) -> None:
        """Весовой A отгружает 0.15, затем B=3.75 подтверждается при текущем спросе 6.85 без округления."""
        self.pf.item = replace(
            self.pf.item,
            base_uom=UomCodeVO("KG"),
            quantity_rules=QuantityRulesVO(Decimal("0.05")),
        )
        self.pf.demand = replace(
            self.pf.demand,
            lines=tuple(
                replace(row, base_uom=UomCodeVO("KG")) for row in self.pf.demand.lines
            ),
        )
        a = self.pf.create_allocation(quantity=QuantityVO(Decimal("3.25")))
        b = self.pf.create_allocation(
            source=self.rf.second.source, quantity=QuantityVO(Decimal("3.75"))
        )
        planned = self.pf.mark(self.pf.add(self.pf.add(self.pf.draft, a), b))
        a_res, b_res = self.rf.reserve(a), self.rf.reserve(b)
        partial = self.rf.confirm(
            planned,
            bindings=(self.rf.binding(a, a_res),),
            reservations=(a_res.fulfillment_snapshot(),),
        )
        order = replace(
            self.sf.order,
            lines=tuple(
                replace(row, base_uom=UomCodeVO("KG")) for row in self.sf.order.lines
            ),
        )
        draft = self.sf.create(
            fulfillment_plan=partial.shipment_snapshot(),
            reservations=(a_res.fulfillment_snapshot(),),
            line_bindings=(
                FulfillmentShipmentLineBindingVO(a.id, ShipmentLineIdVO(uuid4())),
            ),
            order=order,
        )
        partial, shipment = self.sf.assign_and_confirm(
            partial,
            draft,
            reservations=(a_res.fulfillment_snapshot(),),
            order=order,
        )
        fact = self.f.execute(shipment, {shipment.lines[0].id: "0.15"})
        with localcontext() as context:
            context.prec = 1
            context.traps[Inexact] = True
            context.traps[Rounded] = True
            after_a = self.f.register(partial, fact)
            covered = after_a.confirm_reservations(
                bindings=(self.rf.binding(b, b_res),),
                reservations=(b_res.fulfillment_snapshot(),),
                demand=self.demand("6.85"),
                inventory_items=(self.pf.item,),
                warehouses=(self.pf.b,),
                expected_version=after_a.version,
                updated_at=self.at,
            )
            self.assertTrue(covered.is_fully_confirmed())
            self.assertEqual(
                covered.get_allocation(a.id).fulfilled_qty.value, Decimal("0.15")
            )
            self.assertEqual(
                covered.get_allocation(a.id).remaining_to_fulfill().value,
                Decimal("3.10"),
            )


if __name__ == "__main__":
    unittest.main()
