"""Допланирование свободной потребности действующего FulfillmentPlan без изменения прежних обязательств."""

import unittest
from dataclasses import replace
from datetime import timedelta, timezone
from decimal import Decimal, Inexact, Rounded, localcontext
from uuid import uuid4

from test import test_inventory_fulfillment_replanning_domain as replanning_fixture
from test import test_inventory_fulfillment_progress_domain as progress_fixture
from src.modules.inventory.domain.error import InventoryError
from src.modules.inventory.domain.fulfillment_plan.aggregate import FulfillmentPlan
from src.modules.inventory.domain.fulfillment_plan.value_object.allocation_id import (
    FulfillmentAllocationIdVO,
)
from src.modules.inventory.domain.fulfillment_plan.value_object.allocation_status import (
    FulfillmentAllocationStatus,
)
from src.modules.inventory.domain.fulfillment_plan.value_object.order_ref import (
    FulfillmentOrderRefVO,
)
from src.modules.inventory.domain.fulfillment_plan.value_object.status import (
    FulfillmentPlanStatus,
)
from src.modules.inventory.domain.inventory_item.value_object.identifier import (
    InventoryItemIdVO,
)
from src.modules.inventory.domain.shipment.value_object.fulfillment_line_binding import (
    FulfillmentShipmentLineBindingVO,
)
from src.modules.inventory.domain.shipment.value_object.line_id import ShipmentLineIdVO
from src.modules.inventory.domain.stock_reservation.value_object.source import (
    ReservationSourceVO,
)
from src.modules.inventory.domain.value_object.quantity import QuantityVO
from src.modules.inventory.domain.value_object.quantity_rules import QuantityRulesVO
from src.modules.inventory.domain.value_object.uom_code import UomCodeVO


class FulfillmentDemandExtensionDomainTests(unittest.TestCase):
    """Проверяет свежие строки, точную потребность, историю и полный путь Shipment после допланирования."""

    def setUp(self) -> None:
        """Готовит PLANNED/CONFIRMED A=3 из потребности 7 и свежий B=4 без резервов."""
        self.f = replanning_fixture.FulfillmentReplanningDomainTests()
        self.f.setUp()
        self.pf, self.rf = self.f.pf, self.f.rf
        self.plan = self.pf.mark()
        self.at = self.f.at
        self.extra = self.rf.second
        self.confirmed = self.rf.confirm(
            self.plan,
            bindings=(self.rf.first_binding,),
            reservations=(self.rf.first_reservation.fulfillment_snapshot(),),
            warehouses=(self.pf.a,),
            updated_at=self.at,
        )

    def extend(
        self, plan: FulfillmentPlan | None = None, **changes: object
    ) -> FulfillmentPlan:
        """Дополняет план B=4 по текущей версии и ровно снимкам действующих не начатых строк."""
        target = self.plan if plan is None else plan
        return target.allocate_remaining_demand(
            **(
                dict(
                    allocations=(self.extra,),
                    demand=self.pf.demand,
                    inventory_items=(self.pf.item,),
                    warehouses=(self.pf.a, self.pf.b),
                    expected_version=target.version,
                    updated_at=max(target.updated_at, self.at),
                )
                | changes
            )
        )

    def test_planned_extension_adds_fresh_rows_once(self) -> None:
        """Новые намерения добавляются без изменения прежней строки или её исходного корня."""
        result = self.extend()
        self.assertEqual(result.version, self.plan.version + 1)
        self.assertEqual(result.status, FulfillmentPlanStatus.PLANNED)
        self.assertIs(result.allocations[0], self.plan.allocations[0])
        self.assertIs(result.allocations[1], self.extra)
        self.assertEqual(
            result.allocations[1].status, FulfillmentAllocationStatus.PLANNED
        )
        self.assertIsNone(result.allocations[1].reservation)
        self.assertEqual(
            result.remaining_to_allocate(self.pf.line_ref, demand=self.pf.demand),
            QuantityVO(Decimal(0)),
        )
        self.assertEqual(len(self.plan.allocations), 1)
        self.f.restore(result)

    def test_confirmed_plan_becomes_partially_confirmed_preserving_reserve(
        self,
    ) -> None:
        """A сохраняет прежнее подтверждение, B остаётся новым намерением."""
        result = self.extend(self.confirmed)
        self.assertEqual(result.status, FulfillmentPlanStatus.PARTIALLY_CONFIRMED)
        self.assertIs(result.allocations[0], self.confirmed.allocations[0])
        self.assertIs(
            result.allocations[0].reservation, self.confirmed.allocations[0].reservation
        )
        self.assertFalse(result.is_fully_confirmed())
        result.shipment_snapshot().ensure_valid()

    def test_partial_coverage_can_leave_unallocated_demand(self) -> None:
        """Допланирование не требует закрыть всю потребность сразу."""
        extra = replace(self.extra, quantity=QuantityVO(Decimal(2)))
        result = self.extend(allocations=(extra,))
        self.assertEqual(
            result.remaining_to_allocate(self.pf.line_ref, demand=self.pf.demand),
            QuantityVO(Decimal(2)),
        )

    def test_batch_can_add_multiple_sources_and_new_order_line(self) -> None:
        """Пакет охватывает разные склады и новую строку того же заказа одной версией."""
        b = replace(self.extra, quantity=QuantityVO(Decimal(2)))
        c = self.f.new_row(self.f.c, "2")
        other = self.f.new_row(self.pf.b, "2", source_ref=self.pf.other_ref)
        result = self.extend(
            allocations=(b, c, other), warehouses=(self.pf.a, self.pf.b, self.f.c)
        )
        self.assertEqual(result.version, self.plan.version + 1)
        self.assertEqual(len(result.allocations), 4)
        self.assertEqual(
            result.remaining_to_allocate(self.pf.line_ref, demand=self.pf.demand),
            QuantityVO(Decimal(0)),
        )
        self.assertEqual(
            result.remaining_to_allocate(self.pf.other_ref, demand=self.pf.demand),
            QuantityVO(Decimal(3)),
        )

    def test_updated_demand_can_introduce_new_order_line(self) -> None:
        """Новая строка проверяется по свежему снимку, а не только по прежним source_ref плана."""
        reference = ReservationSourceVO("orders", "new-line")
        line = replace(
            self.pf.first_demand,
            source_ref=reference,
            remaining_qty=QuantityVO(Decimal(2)),
        )
        demand = replace(self.pf.demand, lines=(*self.pf.demand.lines, line))
        new = self.f.new_row(self.pf.b, "2", source_ref=reference)
        result = self.extend(allocations=(new,), demand=demand)
        self.assertEqual(result.allocations[-1].source_ref, reference)
        self.assertEqual(
            result.remaining_to_allocate(reference, demand=demand),
            QuantityVO(Decimal(0)),
        )

    def test_partially_confirmed_status_is_preserved(self) -> None:
        """Дополнение плана с подтверждённым A и неподтверждённым B сохраняет прежние строки."""
        partial = self.rf.partial()
        demand = replace(
            self.pf.demand,
            lines=(
                replace(self.pf.first_demand, remaining_qty=QuantityVO(Decimal(9))),
                self.pf.other_demand,
            ),
        )
        new = self.f.new_row(self.f.c, "2")
        result = self.extend(
            partial,
            allocations=(new,),
            demand=demand,
            warehouses=(self.pf.a, self.pf.b, self.f.c),
        )
        self.assertEqual(result.status, FulfillmentPlanStatus.PARTIALLY_CONFIRMED)
        self.assertIs(result.allocations[0], partial.allocations[0])
        self.assertIs(result.allocations[1], partial.allocations[1])

    def test_old_draft_of_unchanged_warehouse_can_assign_and_confirm(self) -> None:
        """Новая B не обесценивает историческое основание черновика A."""
        draft = self.f.draft(
            self.confirmed, self.pf.allocation, self.rf.first_reservation, self.pf.a
        )
        extended = self.extend(self.confirmed)
        assigned, shipment = self.f.assign_and_confirm(
            extended, draft, self.rf.first_reservation, self.pf.a
        )
        self.assertEqual(
            shipment.fulfillment_source.plan_version, self.confirmed.version
        )
        self.assertEqual(
            assigned.allocations[0].shipment_assignment.source_plan_version,
            self.confirmed.version,
        )
        self.assertIs(assigned.allocations[1], extended.allocations[1])

    def test_confirm_new_reserve_and_execute_both_warehouses_to_fulfilled(self) -> None:
        """Допланированный B подтверждается штатно, обе отгрузки завершают один план."""
        extended = self.extend(self.confirmed)
        confirmed = self.rf.confirm(
            extended, bindings=(self.rf.second_binding,), updated_at=self.at
        )
        self.assertEqual(confirmed.status, FulfillmentPlanStatus.CONFIRMED)
        fixture = progress_fixture.FulfillmentProgressDomainTests()
        fixture.setUp()
        fixture.at = self.at
        plan = confirmed
        for row, reserve, warehouse in (
            (self.pf.allocation, self.rf.first_reservation, self.pf.a),
            (self.extra, self.rf.second_reservation, self.pf.b),
        ):
            draft = self.f.draft(plan, row, reserve, warehouse)
            plan, shipment = self.f.assign_and_confirm(plan, draft, reserve, warehouse)
            fact = fixture.execute(
                shipment, {shipment.lines[0].id: str(row.quantity.value)}
            )
            plan = plan.register_shipment(
                fact.fulfillment_snapshot(),
                expected_version=plan.version,
                updated_at=self.at,
            )
        self.assertEqual(plan.status, FulfillmentPlanStatus.FULFILLED)
        self.assertEqual(
            tuple(row.fulfilled_qty.value for row in plan.allocations),
            (Decimal(3), Decimal(4)),
        )
        self.f.restore(plan)

    def test_extension_after_partial_execution_counts_only_remaining_obligations(
        self,
    ) -> None:
        """Факт A=1 сохраняется; после отмены B свободные 4 допланируются на C при потребности 6."""
        f = progress_fixture.FulfillmentProgressDomainTests()
        f.setUp()
        progressed = f.register()
        closed = f.rf.second_reservation.release_all(
            expected_version=1, updated_at=f.at
        )
        released = progressed.release_reservation_confirmations(
            bindings=(f.rf.binding(f.rf.second, closed),),
            reservations=(closed.fulfillment_snapshot(),),
            expected_version=progressed.version,
            updated_at=f.at,
        )
        cancelled = released.cancel_allocations(
            allocation_ids=(f.rf.second.id,),
            expected_version=released.version,
            updated_at=f.at,
        )
        new = f.pf.create_allocation(
            source=replace(f.pf.source, warehouse_id=self.f.c.id),
            quantity=QuantityVO(Decimal(4)),
        )
        demand = replace(
            f.pf.demand,
            lines=(
                replace(f.pf.first_demand, remaining_qty=QuantityVO(Decimal(6))),
                f.pf.other_demand,
            ),
        )
        result = self.extend(
            cancelled,
            allocations=(new,),
            demand=demand,
            inventory_items=(f.pf.item,),
            warehouses=(self.f.c,),
        )
        self.assertEqual(result.status, FulfillmentPlanStatus.PARTIALLY_FULFILLED)
        self.assertIs(result.allocations[0], cancelled.allocations[0])
        self.assertIs(result.allocations[1], cancelled.allocations[1])
        self.assertEqual(
            result.remaining_to_allocate(new.source_ref, demand=demand),
            QuantityVO(Decimal(0)),
        )
        reserve = f.rf.reserve(new)
        confirmed = f.rf.confirm(
            result,
            bindings=(f.rf.binding(new, reserve),),
            reservations=(reserve.fulfillment_snapshot(),),
            demand=demand,
            inventory_items=(f.pf.item,),
            warehouses=(self.f.c,),
            updated_at=self.at,
        )
        draft = f.f.create(
            fulfillment_plan=confirmed.shipment_snapshot(),
            warehouse=self.f.c,
            reservations=(reserve.fulfillment_snapshot(),),
            line_bindings=(
                FulfillmentShipmentLineBindingVO(new.id, ShipmentLineIdVO(uuid4())),
            ),
            created_at=self.at,
        )
        assigned, shipment = f.f.assign_and_confirm(
            confirmed,
            draft,
            warehouse=self.f.c,
            reservations=(reserve.fulfillment_snapshot(),),
            updated_at=self.at,
        )
        fact = f.execute(shipment, {shipment.lines[0].id: "4"}, at=self.at)
        after_c = assigned.register_shipment(
            fact.fulfillment_snapshot(),
            expected_version=assigned.version,
            updated_at=self.at,
        )
        a_fact = f.execute(f.a_partial, {f.a_partial.lines[0].id: "2"}, at=self.at)
        complete = after_c.register_shipment(
            a_fact.fulfillment_snapshot(),
            expected_version=after_c.version,
            updated_at=self.at,
        )
        self.assertEqual(complete.status, FulfillmentPlanStatus.FULFILLED)
        self.assertEqual(
            complete.allocations[1].status, FulfillmentAllocationStatus.CANCELLED
        )

    def test_extension_preserves_closed_reserve_history_and_global_identity(
        self,
    ) -> None:
        """Новая B может заменить отменённое намерение по тому же складу, сохраняя историю старого ID."""
        released, closed = self.f.close_b(self.rf.confirm())
        cancelled = released.cancel_allocations(
            allocation_ids=(self.extra.id,),
            expected_version=released.version,
            updated_at=self.at,
        )
        new = replace(self.extra, id=FulfillmentAllocationIdVO(uuid4()))
        result = self.extend(cancelled, allocations=(new,))
        self.assertIs(result.allocations[1], cancelled.allocations[1])
        self.assertEqual(
            result.allocations[1].reservation_releases[-1].confirmation.reservation_id,
            closed.id,
        )
        self.assertIs(
            result.cancel_allocations(
                allocation_ids=(self.extra.id,),
                expected_version=result.version,
                updated_at=self.at,
            ),
            result,
        )
        reserve = self.rf.reserve(new, identifier=closed.id)
        with self.assertRaises(InventoryError):
            self.rf.confirm(
                result,
                bindings=(self.rf.binding(new, reserve),),
                reservations=(
                    self.rf.first_reservation.fulfillment_snapshot(),
                    reserve.fulfillment_snapshot(),
                ),
                updated_at=self.at,
            )
        result.shipment_snapshot().ensure_valid()

    def test_new_rows_require_new_ids_across_full_history(self) -> None:
        """ID существующей и отменённой строки нельзя повторно использовать."""
        cancelled = self.f.plan.cancel_allocations(
            allocation_ids=(self.extra.id,),
            expected_version=self.f.plan.version,
            updated_at=self.at,
        )
        for identifier in (self.pf.allocation.id, self.extra.id):
            with self.subTest(identifier=identifier), self.assertRaises(InventoryError):
                self.extend(
                    cancelled, allocations=(replace(self.extra, id=identifier),)
                )

    def test_nonempty_tuple_nominal_entities_and_unique_batch_are_required(
        self,
    ) -> None:
        """Пустые, сырые и повторные новые строки не проходят проверку пакета."""
        for allocations in (
            (),
            [],
            [self.extra],
            (object(),),
            (self.extra, self.extra),
        ):
            with (
                self.subTest(allocations=allocations),
                self.assertRaises(InventoryError),
            ):
                self.extend(allocations=allocations)

    def test_new_rows_cannot_carry_confirmation_cancellation_or_history(self) -> None:
        """Добавляются только свежие PLANNED, а не исторические состояния чужой версии плана."""
        released, _ = self.f.close_b(self.rf.confirm())
        variants = (
            self.rf.confirm().allocations[1],
            released.allocations[1],
            self.extra.cancel_unstarted(cancelled_at=self.at),
        )
        for row in variants:
            with self.subTest(status=row.status), self.assertRaises(InventoryError):
                self.extend(
                    allocations=(replace(row, id=FulfillmentAllocationIdVO(uuid4())),)
                )

    def test_zero_raw_quantity_and_non_planned_state_are_rejected(self) -> None:
        """Локальная валидация Entity не заменяется аннотациями входного tuple."""
        for row in (
            replace(self.extra, quantity=QuantityVO(Decimal(0))),
            replace(self.extra, quantity=Decimal(4)),
            replace(self.extra, status="PLANNED"),
        ):
            with self.subTest(row=row), self.assertRaises(InventoryError):
                self.extend(allocations=(row,))

    def test_same_active_order_line_and_source_cannot_be_duplicated(self) -> None:
        """Свободное количество не разрешает вторую действующую Entity той же пары строка/склад."""
        duplicate = self.f.new_row(self.pf.a, "4")
        with self.assertRaises(InventoryError):
            self.extend(allocations=(duplicate,), warehouses=(self.pf.a,))

    def test_new_line_must_match_current_order_item_and_base_uom(self) -> None:
        """Ссылка, товар и базовая единица новых намерений должны принадлежать актуальной потребности."""
        variants = (
            replace(self.extra, source_ref=ReservationSourceVO("orders", "unknown")),
            replace(self.extra, inventory_item_id=InventoryItemIdVO(uuid4())),
            replace(self.extra, base_uom=UomCodeVO("KG")),
        )
        for row in variants:
            with self.subTest(row=row), self.assertRaises(InventoryError):
                self.extend(allocations=(row,))

    def test_current_demand_and_source_split_are_checked_for_whole_candidate(
        self,
    ) -> None:
        """Проверяются актуальность заказа, весь итоговый лимит и разрешение нескольких источников."""
        for demand in (
            replace(self.pf.demand, is_fulfillable=False),
            replace(self.pf.demand, order_ref=FulfillmentOrderRefVO("orders", "other")),
            replace(self.pf.demand, lines=(self.pf.other_demand,)),
            replace(
                self.pf.demand,
                lines=(
                    replace(self.pf.first_demand, remaining_qty=QuantityVO(Decimal(6))),
                    self.pf.other_demand,
                ),
            ),
            replace(
                self.pf.demand,
                lines=(
                    replace(self.pf.first_demand, allow_source_split=False),
                    self.pf.other_demand,
                ),
            ),
        ):
            with self.subTest(demand=demand), self.assertRaises(InventoryError):
                self.extend(demand=demand)
        with self.assertRaises(InventoryError):
            self.extend(
                allocations=(replace(self.extra, quantity=QuantityVO(Decimal(5))),)
            )

    def test_unselected_existing_obligations_also_must_fit_demand(self) -> None:
        """Новая строка заказа не обходит уменьшившуюся потребность старой строки."""
        new = self.f.new_row(self.pf.b, "2", source_ref=self.pf.other_ref)
        demand = replace(
            self.pf.demand,
            lines=(
                replace(self.pf.first_demand, remaining_qty=QuantityVO(Decimal(2))),
                self.pf.other_demand,
            ),
        )
        with self.assertRaises(InventoryError):
            self.extend(allocations=(new,), demand=demand)

    def test_current_item_step_and_active_warehouses_are_required(self) -> None:
        """Свежие настройки применяются к новым и прежним ещё не начатым строкам."""
        for changes in (
            dict(
                allocations=(replace(self.extra, quantity=QuantityVO(Decimal(".5"))),)
            ),
            dict(warehouses=(self.pf.a, replace(self.pf.b, is_active=False))),
            dict(warehouses=(replace(self.pf.a, is_active=False), self.pf.b)),
            dict(
                inventory_items=(
                    replace(self.pf.item, quantity_rules=QuantityRulesVO(Decimal(2))),
                )
            ),
        ):
            with self.subTest(changes=changes), self.assertRaises(InventoryError):
                self.extend(**changes)

    def test_exact_unique_current_context_is_required(self) -> None:
        """Нельзя пропустить прежний склад либо передать лишние или повторные снимки."""
        for changes in (
            dict(warehouses=(self.pf.b,)),
            dict(warehouses=(self.pf.a, self.pf.b, self.f.c)),
            dict(warehouses=(self.pf.a, self.pf.b, self.pf.b)),
            dict(warehouses=[self.pf.a, self.pf.b]),
            dict(inventory_items=()),
            dict(inventory_items=(self.pf.item, self.pf.item)),
            dict(inventory_items=[self.pf.item]),
        ):
            with self.subTest(changes=changes), self.assertRaises(InventoryError):
                self.extend(**changes)

    def test_assigned_warehouse_can_receive_independent_order_line(self) -> None:
        """Новая независимая строка того же склада не расширяет прежнюю группу Shipment."""
        draft = self.f.draft(
            self.confirmed, self.pf.allocation, self.rf.first_reservation, self.pf.a
        )
        assigned = self.confirmed.assign_shipment(
            draft.assignment_snapshot(),
            expected_version=self.confirmed.version,
            updated_at=self.at,
        )
        new = self.f.new_row(self.pf.a, "2", source_ref=self.pf.other_ref)
        extended = self.extend(assigned, allocations=(new,), warehouses=(self.pf.a,))
        self.assertIs(extended.allocations[0], assigned.allocations[0])
        self.assertIsNone(extended.allocations[1].shipment_assignment)
        self.assertEqual(len(assigned.allocations), 1)
        extended.shipment_snapshot().ensure_valid()

    def test_started_warehouse_can_receive_new_independent_allocations(self) -> None:
        """Частично исполненная группа сохраняет контрольную точку при добавлении независимой строки того же склада."""
        draft = self.f.draft(
            self.confirmed, self.pf.allocation, self.rf.first_reservation, self.pf.a
        )
        assigned, shipment = self.f.assign_and_confirm(
            self.confirmed, draft, self.rf.first_reservation, self.pf.a
        )
        f = progress_fixture.FulfillmentProgressDomainTests()
        f.setUp()
        f.at = self.at
        fact = f.execute(shipment)
        plan = assigned.register_shipment(
            fact.fulfillment_snapshot(),
            expected_version=assigned.version,
            updated_at=self.at,
        )
        new = self.f.new_row(self.pf.a, "2", source_ref=self.pf.other_ref)
        extended = self.extend(plan, allocations=(new,), warehouses=(self.pf.a,))
        self.assertIs(extended.allocations[0], plan.allocations[0])
        self.assertEqual(extended.status, FulfillmentPlanStatus.PARTIALLY_FULFILLED)
        extended.shipment_snapshot().ensure_valid()

    def test_adding_other_warehouse_preserves_existing_assignment(self) -> None:
        """Закреплённый A не блокирует допланирование свободного B и подтверждение прежнего A."""
        draft = self.f.draft(
            self.confirmed, self.pf.allocation, self.rf.first_reservation, self.pf.a
        )
        assigned = self.confirmed.assign_shipment(
            draft.assignment_snapshot(),
            expected_version=self.confirmed.version,
            updated_at=self.at,
        )
        result = self.extend(assigned)
        self.assertIs(result.allocations[0], assigned.allocations[0])
        shipment = draft.confirm_from_fulfillment_plan(
            expected_version=0,
            fulfillment_plan=result.shipment_snapshot(),
            warehouse=self.pf.a,
            order=self.f.order,
            inventory_items=(self.pf.item,),
            reservations=(self.rf.first_reservation.fulfillment_snapshot(),),
            updated_at=self.at,
        )
        self.assertEqual(
            shipment.fulfillment_source.plan_version, self.confirmed.version
        )

    def test_old_unassigned_draft_keeps_selected_group_when_warehouse_grows(
        self,
    ) -> None:
        """Расширение склада не изменяет явно выбранный состав прежнего черновика."""
        draft = self.f.draft(
            self.confirmed, self.pf.allocation, self.rf.first_reservation, self.pf.a
        )
        other = self.f.new_row(self.pf.a, "2", source_ref=self.pf.other_ref)
        result = self.extend(
            self.confirmed, allocations=(other,), warehouses=(self.pf.a,)
        )
        assigned = result.assign_shipment(
            draft.assignment_snapshot(),
            expected_version=result.version,
            updated_at=self.at,
        )
        shipment = draft.confirm_from_fulfillment_plan(
            expected_version=0,
            fulfillment_plan=assigned.shipment_snapshot(),
            warehouse=self.pf.a,
            order=self.f.order,
            inventory_items=(self.pf.item,),
            reservations=(self.rf.first_reservation.fulfillment_snapshot(),),
            updated_at=self.at,
        )
        self.assertEqual(len(shipment.lines), 1)
        self.assertIsNone(assigned.allocations[1].shipment_assignment)

    def test_stale_version_and_invalid_time_are_rejected(self) -> None:
        """Версия строгая без bool, время явное aware и неубывающее."""
        for changes in (
            dict(expected_version=True),
            dict(expected_version=-1),
            dict(expected_version=self.plan.version - 1),
            dict(updated_at=self.plan.updated_at - timedelta(seconds=1)),
            dict(updated_at=self.at.replace(tzinfo=None)),
            dict(updated_at="now"),
        ):
            with self.subTest(changes=changes), self.assertRaises(InventoryError):
                self.extend(**changes)
        result = self.extend(
            updated_at=self.at.astimezone(timezone(timedelta(hours=3)))
        )
        self.assertEqual(result.updated_at, self.at)

    def test_reusing_ids_or_stale_version_does_not_repeat_addition(self) -> None:
        """Повтор команды не дублирует намерение даже при увеличенной свежей потребности."""
        result = self.extend()
        demand = replace(
            self.pf.demand,
            lines=(
                replace(self.pf.first_demand, remaining_qty=QuantityVO(Decimal(20))),
                self.pf.other_demand,
            ),
        )
        with self.assertRaises(InventoryError):
            self.extend(result, expected_version=self.plan.version)
        with self.assertRaises(InventoryError):
            self.extend(result, demand=demand)
        self.assertEqual(len(result.allocations), 2)

    def test_draft_and_cancelled_plan_cannot_be_extended(self) -> None:
        """Черновик сохраняет прежний интерфейс, отменённый корень терминален."""
        cancelled = self.plan.cancel(
            expected_version=self.plan.version, updated_at=self.at
        )
        for plan in (self.pf.one, cancelled):
            with self.subTest(status=plan.status), self.assertRaises(InventoryError):
                self.extend(plan)

    def test_fulfilled_plan_cannot_be_reopened_for_remaining_order_demand(self) -> None:
        """Завершение действующего состава терминально даже при неполном покрытии заказа."""
        draft = self.f.draft(
            self.confirmed, self.pf.allocation, self.rf.first_reservation, self.pf.a
        )
        assigned, shipment = self.f.assign_and_confirm(
            self.confirmed, draft, self.rf.first_reservation, self.pf.a
        )
        f = progress_fixture.FulfillmentProgressDomainTests()
        f.setUp()
        f.at = self.at
        fact = f.execute(shipment, {shipment.lines[0].id: "3"})
        complete = assigned.register_shipment(
            fact.fulfillment_snapshot(),
            expected_version=assigned.version,
            updated_at=self.at,
        )
        self.assertEqual(complete.status, FulfillmentPlanStatus.FULFILLED)
        with self.assertRaises(InventoryError):
            self.extend(complete)

    def test_invalid_last_row_leaves_entire_original_unchanged(self) -> None:
        """Ошибка последней строки не добавляет первую и не меняет версию."""
        invalid = self.f.new_row(self.f.c, "2")
        with self.assertRaises(InventoryError):
            self.extend(
                allocations=(self.extra, invalid),
                warehouses=(self.pf.a, self.pf.b, self.f.c),
            )
        self.assertEqual(len(self.plan.allocations), 1)
        self.assertEqual(self.plan.version, 2)

    def test_fractional_extension_preserves_exact_arithmetic_in_small_context(
        self,
    ) -> None:
        """Внешняя Decimal precision не округляет суммы потребности и новых намерений."""
        item = replace(
            self.pf.item,
            base_uom=UomCodeVO("KG"),
            quantity_rules=QuantityRulesVO(Decimal(".000001")),
        )
        old = replace(
            self.plan.allocations[0],
            base_uom=item.base_uom,
            quantity=QuantityVO(Decimal(".123456")),
        )
        plan = self.f.restore(self.plan, allocations=(old,))
        new = replace(
            self.extra, base_uom=item.base_uom, quantity=QuantityVO(Decimal(".654321"))
        )
        demand = replace(
            self.pf.demand,
            lines=(
                replace(
                    self.pf.first_demand,
                    base_uom=item.base_uom,
                    remaining_qty=QuantityVO(Decimal(".777777")),
                ),
            ),
        )
        with localcontext() as ctx:
            ctx.prec = 2
            ctx.traps[Inexact] = True
            ctx.traps[Rounded] = True
            result = self.extend(
                plan, allocations=(new,), demand=demand, inventory_items=(item,)
            )
            remaining = result.remaining_to_allocate(old.source_ref, demand=demand)
        self.assertEqual(remaining, QuantityVO(Decimal(0)))
        self.assertEqual(result.allocations[-1].quantity, new.quantity)


if __name__ == "__main__":
    unittest.main()
