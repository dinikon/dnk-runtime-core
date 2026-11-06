"""Перепланирование не начатых Allocation с сохранением отменённой истории и пути исполнения."""

import unittest
from dataclasses import fields, replace
from datetime import timedelta, timezone
from decimal import Decimal, Inexact, Rounded, localcontext
from uuid import uuid4

from test import test_inventory_fulfillment_reservation_domain as reservation_fixture
from test import test_inventory_fulfillment_progress_domain as progress_fixture
from test import test_inventory_shipment_assignment_domain as assignment_fixture
from src.modules.inventory.domain.error import InventoryError
from src.modules.inventory.domain.fulfillment_plan.aggregate import FulfillmentPlan
from src.modules.inventory.domain.fulfillment_plan.entity.fulfillment_allocation import (
    FulfillmentAllocation,
)
from src.modules.inventory.domain.fulfillment_plan.value_object.allocation_id import (
    FulfillmentAllocationIdVO,
)
from src.modules.inventory.domain.fulfillment_plan.value_object.allocation_status import (
    FulfillmentAllocationStatus,
)
from src.modules.inventory.domain.fulfillment_plan.value_object.status import (
    FulfillmentPlanStatus,
)
from src.modules.inventory.domain.fulfillment_plan.value_object.order_ref import (
    FulfillmentOrderRefVO,
)
from src.modules.inventory.domain.shipment.aggregate import Shipment
from src.modules.inventory.domain.shipment.order_snapshot import (
    ShipmentOrderSnapshot,
    ShipmentOrderLineSnapshot,
)
from src.modules.inventory.domain.shipment.value_object.identifier import ShipmentIdVO
from src.modules.inventory.domain.shipment.value_object.line_id import ShipmentLineIdVO
from src.modules.inventory.domain.shipment.value_object.order_ref import (
    ShipmentOrderRefVO,
)
from src.modules.inventory.domain.shipment.value_object.fulfillment_line_binding import (
    FulfillmentShipmentLineBindingVO,
)
from src.modules.inventory.domain.stock_reservation.aggregate import StockReservation
from src.modules.inventory.domain.value_object.quantity import QuantityVO
from src.modules.inventory.domain.value_object.quantity_rules import QuantityRulesVO
from src.modules.inventory.domain.value_object.uom_code import UomCodeVO
from src.modules.inventory.domain.warehouse.snapshot import WarehouseSnapshot
from src.modules.inventory.domain.warehouse.value_object.identifier import WarehouseIdVO


class FulfillmentReplanningDomainTests(unittest.TestCase):
    """Проверяет атомарную замену состава, ограничения истории и исполнение после замены."""

    def setUp(self) -> None:
        """Готовит PLANNED A=3/B=4 и новую строку C=4 для того же заказа."""
        self.rf = reservation_fixture.FulfillmentReservationDomainTests()
        self.rf.setUp()
        self.pf = self.rf.f
        self.plan = self.rf.plan
        self.at = self.rf.at + timedelta(minutes=2)
        self.c = WarehouseSnapshot(WarehouseIdVO(uuid4()), True, None)
        self.d = WarehouseSnapshot(WarehouseIdVO(uuid4()), True, None)
        self.replacement = self.new_row(self.c, "4")
        self.order = ShipmentOrderSnapshot(
            ShipmentOrderRefVO(
                self.plan.order_ref.system, self.plan.order_ref.reference
            ),
            True,
            tuple(
                ShipmentOrderLineSnapshot(
                    line.source_ref,
                    line.inventory_item_id,
                    line.base_uom,
                    line.remaining_qty,
                )
                for line in self.pf.demand.lines
            ),
        )

    def new_row(
        self, warehouse: WarehouseSnapshot, quantity: str, **changes: object
    ) -> FulfillmentAllocation:
        """Создаёт свежий положительный PLANNED без истории через фабрику Entity."""
        return self.pf.create_allocation(
            **(
                dict(
                    source=replace(self.pf.source, warehouse_id=warehouse.id),
                    quantity=QuantityVO(Decimal(quantity)),
                )
                | changes
            )
        )

    def replan(
        self, plan: FulfillmentPlan | None = None, **changes: object
    ) -> FulfillmentPlan:
        """Вызывает корень с явной текущей версией и контекстом действующих не начатых строк."""
        target = self.plan if plan is None else plan
        return target.replan_allocations(
            **(
                dict(
                    allocation_ids=(self.rf.second.id,),
                    replacements=(self.replacement,),
                    demand=self.pf.demand,
                    inventory_items=(self.pf.item,),
                    warehouses=(self.pf.a, self.c),
                    expected_version=target.version,
                    updated_at=max(target.updated_at, self.at),
                )
                | changes
            )
        )

    def restore(self, plan: FulfillmentPlan, **changes: object) -> FulfillmentPlan:
        """Проверяет восстановление полного исторического состава без внешнего контекста."""
        values = {field.name: getattr(plan, field.name) for field in fields(plan)}
        values["identifier"] = values.pop("id")
        return FulfillmentPlan.restore(**(values | changes))

    def close_b(
        self, plan: FulfillmentPlan
    ) -> tuple[FulfillmentPlan, StockReservation]:
        """Закрывает реальный резерв B и отдельно снимает его подтверждение в плане."""
        closed = self.rf.second_reservation.release_all(
            expected_version=1, updated_at=self.at
        )
        return (
            plan.release_reservation_confirmations(
                bindings=(self.rf.binding(self.rf.second, closed),),
                reservations=(closed.fulfillment_snapshot(),),
                expected_version=plan.version,
                updated_at=self.at,
            ),
            closed,
        )

    def confirm_c(
        self, plan: FulfillmentPlan
    ) -> tuple[FulfillmentPlan, StockReservation]:
        """Подтверждает новую строку новым резервом, повторно проверяя действующий A."""
        reserve = self.rf.reserve(self.replacement)
        result = self.rf.confirm(
            plan,
            bindings=(self.rf.binding(self.replacement, reserve),),
            reservations=(
                self.rf.first_reservation.fulfillment_snapshot(),
                reserve.fulfillment_snapshot(),
            ),
            warehouses=(self.pf.a, self.c),
            updated_at=self.at,
        )
        return result, reserve

    def draft(
        self,
        plan: FulfillmentPlan,
        row: FulfillmentAllocation,
        reserve: StockReservation,
        warehouse: WarehouseSnapshot,
    ) -> Shipment:
        """Строит Shipment выбранного склада через штатную фабрику по полному снимку с историей."""
        return Shipment.create_from_fulfillment_plan(
            identifier=ShipmentIdVO(uuid4()),
            fulfillment_plan=plan.shipment_snapshot(),
            warehouse=warehouse,
            order=self.order,
            inventory_items=(self.pf.item,),
            reservations=(reserve.fulfillment_snapshot(),),
            line_bindings=(
                FulfillmentShipmentLineBindingVO(row.id, ShipmentLineIdVO(uuid4())),
            ),
            created_at=self.at,
        )

    def assign_and_confirm(
        self,
        plan: FulfillmentPlan,
        draft: Shipment,
        reserve: StockReservation,
        warehouse: WarehouseSnapshot,
    ) -> tuple[FulfillmentPlan, Shipment]:
        """Назначает полный действующий склад и подтверждает отгрузку свежим основанием."""
        assigned = plan.assign_shipment(
            draft.assignment_snapshot(),
            expected_version=plan.version,
            updated_at=self.at,
        )
        shipment = draft.confirm_from_fulfillment_plan(
            expected_version=draft.version,
            fulfillment_plan=assigned.shipment_snapshot(),
            warehouse=warehouse,
            order=self.order,
            inventory_items=(self.pf.item,),
            reservations=(reserve.fulfillment_snapshot(),),
            updated_at=self.at,
        )
        return assigned, shipment

    def test_replacement_keeps_old_identity_and_appends_new_planned_row(self) -> None:
        """Смена B на C меняет одну версию и сохраняет исходную Entity как историю."""
        result = self.replan()
        old, cancelled, new = (
            self.rf.second,
            result.allocations[1],
            result.allocations[2],
        )
        self.assertIs(result.allocations[0], self.plan.allocations[0])
        self.assertEqual(
            cancelled,
            replace(
                old, status=FulfillmentAllocationStatus.CANCELLED, cancelled_at=self.at
            ),
        )
        self.assertEqual(cancelled.remaining_to_fulfill(), QuantityVO(Decimal(0)))
        self.assertEqual(new, self.replacement)
        self.assertEqual(result.status, FulfillmentPlanStatus.PLANNED)
        self.assertEqual(result.version, self.plan.version + 1)
        self.assertEqual(
            result.remaining_to_allocate(old.source_ref, demand=self.pf.demand),
            QuantityVO(Decimal(0)),
        )
        self.assertEqual(old.status, FulfillmentAllocationStatus.PLANNED)
        self.assertIsNone(old.cancelled_at)

    def test_quantity_can_be_reduced_without_overwriting_history(self) -> None:
        """Уменьшение намерения оставляет часть потребности нераспределённой."""
        new = self.new_row(self.c, "2")
        result = self.replan(replacements=(new,))
        self.assertEqual(result.allocations[1].quantity, QuantityVO(Decimal(4)))
        self.assertEqual(
            result.remaining_to_allocate(new.source_ref, demand=self.pf.demand),
            QuantityVO(Decimal(2)),
        )

    def test_same_warehouse_replacement_is_allowed_but_active_duplicate_is_not(
        self,
    ) -> None:
        """Пара строка/склад уникальна среди действующих строк, а история может совпадать."""
        new = self.new_row(self.pf.b, "4")
        result = self.replan(replacements=(new,), warehouses=(self.pf.a, self.pf.b))
        self.restore(result)
        with self.assertRaises(InventoryError):
            self.replan(
                replacements=(self.new_row(self.pf.a, "4"),), warehouses=(self.pf.a,)
            )

    def test_split_one_allocation_across_two_warehouses(self) -> None:
        """Одна отменённая строка заменяется двумя новыми без увеличения общего обязательства."""
        c, d = self.new_row(self.c, "2"), self.new_row(self.d, "2")
        result = self.replan(
            replacements=(c, d), warehouses=(self.pf.a, self.c, self.d)
        )
        self.assertEqual(len(result.allocations), 4)
        self.assertEqual(
            result.remaining_to_allocate(c.source_ref, demand=self.pf.demand),
            QuantityVO(Decimal(0)),
        )

    def test_merge_two_allocations_into_one(self) -> None:
        """Два намерения заменяются одним, обе исходные строки остаются в истории."""
        new = self.new_row(self.c, "7")
        result = self.replan(
            allocation_ids=tuple(row.id for row in self.plan.allocations),
            replacements=(new,),
            warehouses=(self.c,),
        )
        self.assertTrue(
            all(
                row.status is FulfillmentAllocationStatus.CANCELLED
                for row in result.allocations[:2]
            )
        )
        self.assertEqual(result.allocations[2], new)
        self.assertEqual(result.version, self.plan.version + 1)

    def test_distinct_selected_order_lines_can_be_replanned_together(self) -> None:
        """Пакет сохраняет отдельную идентичность и лимиты каждой выбранной строки заказа."""
        extra = self.pf.create_allocation(
            source_ref=self.pf.other_ref, quantity=QuantityVO(Decimal(2))
        )
        plan = self.pf.mark(
            self.pf.add(self.pf.add(self.pf.one, self.rf.second), extra)
        )
        second = self.new_row(self.c, "2", source_ref=self.pf.other_ref)
        result = self.replan(
            plan,
            allocation_ids=(self.rf.second.id, extra.id),
            replacements=(self.replacement, second),
        )
        self.assertEqual(result.allocations[-1].source_ref, self.pf.other_ref)
        self.assertEqual(
            result.remaining_to_allocate(self.pf.other_ref, demand=self.pf.demand),
            QuantityVO(Decimal(3)),
        )

    def test_new_rows_cannot_introduce_unselected_order_line(self) -> None:
        """Перепланирование не превращается в неявное добавление новой строки заказа."""
        new = self.new_row(self.c, "4", source_ref=self.pf.other_ref)
        with self.assertRaises(InventoryError):
            self.replan(replacements=(new,))

    def test_released_reserve_history_remains_globally_occupied(self) -> None:
        """Отмена строки не освобождает старый резервный ID для нового подтверждения."""
        released, closed = self.close_b(self.rf.confirm())
        result = self.replan(released)
        self.assertEqual(result.status, FulfillmentPlanStatus.PARTIALLY_CONFIRMED)
        self.assertEqual(
            result.allocations[1].reservation_releases,
            released.allocations[1].reservation_releases,
        )
        fresh = self.rf.reserve(self.replacement, identifier=closed.id)
        with self.assertRaises(InventoryError):
            self.rf.confirm(
                result,
                bindings=(self.rf.binding(self.replacement, fresh),),
                reservations=(
                    self.rf.first_reservation.fulfillment_snapshot(),
                    fresh.fulfillment_snapshot(),
                ),
                warehouses=(self.pf.a, self.c),
                updated_at=self.at,
            )

    def test_historical_release_replay_does_not_revive_cancelled_row(self) -> None:
        """Повтор закрытия прежнего резерва сохраняет терминальную строку и версию плана."""
        released, closed = self.close_b(self.rf.confirm())
        result = self.replan(released)
        repeated = result.release_reservation_confirmations(
            bindings=(self.rf.binding(self.rf.second, closed),),
            reservations=(closed.fulfillment_snapshot(),),
            expected_version=result.version,
            updated_at=self.at,
        )
        self.assertIs(repeated, result)
        self.assertEqual(
            repeated.allocations[1].status, FulfillmentAllocationStatus.CANCELLED
        )

    def test_confirm_new_reserve_ignores_cancelled_scope_in_snapshot(self) -> None:
        """После подтверждения новой строки старый B не требует текущих снимков или резервов."""
        released, _ = self.close_b(self.rf.confirm())
        replanned = self.replan(released)
        result, reserve = self.confirm_c(replanned)
        self.assertEqual(result.status, FulfillmentPlanStatus.CONFIRMED)
        self.assertTrue(result.is_fully_confirmed())
        snapshot = result.shipment_snapshot()
        snapshot.ensure_valid()
        self.assertEqual(snapshot.allocations[1].cancelled_at, self.at)
        self.assertEqual(snapshot.allocations[2].reservation.reservation_id, reserve.id)

    def test_execution_reaches_fulfilled_despite_cancelled_history(self) -> None:
        """Обе действующие отгрузки завершают план; отменённая B не мешает FULFILLED."""
        released, _ = self.close_b(self.rf.confirm())
        plan, reserve_c = self.confirm_c(self.replan(released))
        fixture = progress_fixture.FulfillmentProgressDomainTests()
        fixture.setUp()
        fixture.at = self.at
        for row, reserve, warehouse in (
            (self.pf.allocation, self.rf.first_reservation, self.pf.a),
            (self.replacement, reserve_c, self.c),
        ):
            draft = self.draft(plan, row, reserve, warehouse)
            plan, shipment = self.assign_and_confirm(plan, draft, reserve, warehouse)
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
            plan.allocations[1].status, FulfillmentAllocationStatus.CANCELLED
        )
        self.assertEqual(plan.allocations[1].fulfilled_qty, QuantityVO(Decimal(0)))
        with self.assertRaises(InventoryError):
            self.replan(plan)
        self.restore(plan)
        self.assertIs(
            plan.register_shipment(
                fact.fulfillment_snapshot(),
                expected_version=plan.version,
                updated_at=self.at,
            ),
            plan,
        )

    def test_same_warehouse_history_is_excluded_from_shipment_scope(self) -> None:
        """Shipment B содержит новую строку B и не требует отменённую предшественницу."""
        released, _ = self.close_b(self.rf.confirm())
        new = self.new_row(self.pf.b, "4")
        plan = self.replan(
            released, replacements=(new,), warehouses=(self.pf.a, self.pf.b)
        )
        reserve = self.rf.reserve(new)
        plan = self.rf.confirm(
            plan,
            bindings=(self.rf.binding(new, reserve),),
            reservations=(
                self.rf.first_reservation.fulfillment_snapshot(),
                reserve.fulfillment_snapshot(),
            ),
            updated_at=self.at,
        )
        draft = self.draft(plan, new, reserve, self.pf.b)
        assigned, shipment = self.assign_and_confirm(plan, draft, reserve, self.pf.b)
        self.assertEqual(
            tuple(line.fulfillment_allocation_id for line in shipment.lines), (new.id,)
        )
        assigned.shipment_snapshot().ensure_valid()
        fixture = progress_fixture.FulfillmentProgressDomainTests()
        fixture.setUp()
        fixture.at = self.at
        fact = fixture.execute(shipment)
        progressed = assigned.register_shipment(
            fact.fulfillment_snapshot(),
            expected_version=assigned.version,
            updated_at=self.at,
        )
        progressed.shipment_snapshot().ensure_valid()
        self.assertIs(progressed.allocations[1], plan.allocations[1])

    def test_old_draft_cannot_assign_or_confirm_after_replanning(self) -> None:
        """Исторический черновик по отменённой Allocation не получает новое основание."""
        confirmed = self.rf.confirm()
        old_draft = self.draft(
            confirmed, self.rf.second, self.rf.second_reservation, self.pf.b
        )
        released, _ = self.close_b(confirmed)
        result = self.replan(released)
        with self.assertRaises(InventoryError):
            result.assign_shipment(
                old_draft.assignment_snapshot(),
                expected_version=result.version,
                updated_at=self.at,
            )
        with self.assertRaises(InventoryError):
            old_draft.confirm_from_fulfillment_plan(
                expected_version=0,
                fulfillment_plan=result.shipment_snapshot(),
                warehouse=self.pf.b,
                order=self.order,
                inventory_items=(self.pf.item,),
                reservations=(self.rf.second_reservation.fulfillment_snapshot(),),
                updated_at=self.at,
            )

    def test_partial_fulfillment_is_preserved_and_only_remaining_demand_is_counted(
        self,
    ) -> None:
        """После A=1 из 3 перенос B=4 оставляет суммарное обязательство 2+4, без повторного вычета факта."""
        f = progress_fixture.FulfillmentProgressDomainTests()
        f.setUp()
        plan = f.register()
        closed = f.rf.second_reservation.release_all(
            expected_version=1, updated_at=f.at
        )
        released = plan.release_reservation_confirmations(
            bindings=(f.rf.binding(f.rf.second, closed),),
            reservations=(closed.fulfillment_snapshot(),),
            expected_version=plan.version,
            updated_at=f.at,
        )
        new = f.pf.create_allocation(
            source=replace(f.pf.source, warehouse_id=self.c.id),
            quantity=QuantityVO(Decimal(4)),
        )
        demand = replace(
            f.pf.demand,
            lines=(
                replace(f.pf.first_demand, remaining_qty=QuantityVO(Decimal(6))),
                f.pf.other_demand,
            ),
        )
        result = self.replan(
            released,
            allocation_ids=(f.rf.second.id,),
            replacements=(new,),
            demand=demand,
            inventory_items=(f.pf.item,),
            warehouses=(self.c,),
            updated_at=max(self.at, f.at),
        )
        self.assertIs(result.allocations[0], released.allocations[0])
        self.assertEqual(result.status, FulfillmentPlanStatus.PARTIALLY_FULFILLED)
        self.assertEqual(
            result.remaining_to_allocate(new.source_ref, demand=demand),
            QuantityVO(Decimal(0)),
        )
        result.shipment_snapshot().ensure_valid()
        reserve = f.rf.reserve(new)
        confirmed = f.rf.confirm(
            result,
            bindings=(f.rf.binding(new, reserve),),
            reservations=(reserve.fulfillment_snapshot(),),
            warehouses=(self.c,),
            demand=demand,
            updated_at=self.at,
        )
        draft = f.f.create(
            fulfillment_plan=confirmed.shipment_snapshot(),
            warehouse=self.c,
            reservations=(reserve.fulfillment_snapshot(),),
            line_bindings=(
                FulfillmentShipmentLineBindingVO(new.id, ShipmentLineIdVO(uuid4())),
            ),
            created_at=self.at,
        )
        assigned, shipment = f.f.assign_and_confirm(
            confirmed,
            draft,
            warehouse=self.c,
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
        self.assertEqual(complete.allocations[0].fulfilled_qty, QuantityVO(Decimal(3)))
        self.assertEqual(
            complete.allocations[1].status, FulfillmentAllocationStatus.CANCELLED
        )

    def test_assigned_or_started_allocation_cannot_be_selected(self) -> None:
        """Нельзя обойти действующий Shipment даже если команда содержит новые строки."""
        f = assignment_fixture.ShipmentAssignmentDomainTests()
        f.setUp()
        with self.assertRaises(InventoryError):
            self.replan(f.assigned, allocation_ids=(f.assigned.allocations[0].id,))
        p = progress_fixture.FulfillmentProgressDomainTests()
        p.setUp()
        started = p.register()
        with self.assertRaises(InventoryError):
            self.replan(started, allocation_ids=(started.allocations[0].id,))

    def test_replacement_cannot_add_rows_to_assigned_warehouse(self) -> None:
        """Полный состав назначенного склада не расширяется неявно при замене другой строки."""
        f = assignment_fixture.ShipmentAssignmentDomainTests()
        f.setUp()
        closed = f.f.f.second_reservation.release_all(
            expected_version=1, updated_at=f.at
        )
        plan = f.assigned.release_reservation_confirmations(
            bindings=(f.f.f.binding(f.f.f.second, closed),),
            reservations=(closed.fulfillment_snapshot(),),
            expected_version=f.assigned.version,
            updated_at=f.at,
        )
        new = f.f.f.f.create_allocation(quantity=QuantityVO(Decimal(4)))
        with self.assertRaises(InventoryError):
            self.replan(
                plan,
                allocation_ids=(f.f.f.second.id,),
                replacements=(new,),
                inventory_items=(f.f.f.f.item,),
                warehouses=(f.f.f.f.a,),
            )

    def test_confirmed_reserve_must_be_released_before_replanning(self) -> None:
        """Действующее подтверждение нельзя удалить самой операцией перепланирования."""
        partial = self.rf.partial()
        with self.assertRaises(InventoryError):
            self.replan(
                partial,
                allocation_ids=(partial.allocations[0].id,),
                replacements=(self.new_row(self.c, "3"),),
            )

    def test_empty_raw_duplicate_and_unknown_selections_are_rejected(self) -> None:
        """Выбор строк и новых Entity должен быть непустым, типизированным и уникальным."""
        cases = (
            dict(allocation_ids=()),
            dict(allocation_ids=[self.rf.second.id]),
            dict(allocation_ids=("raw",)),
            dict(allocation_ids=(FulfillmentAllocationIdVO(uuid4()),)),
            dict(allocation_ids=(self.rf.second.id, self.rf.second.id)),
            dict(replacements=()),
            dict(replacements=[self.replacement]),
            dict(replacements=(object(),)),
            dict(replacements=(self.replacement, self.replacement)),
        )
        for changes in cases:
            with self.subTest(changes=changes), self.assertRaises(InventoryError):
                self.replan(**changes)

    def test_historical_and_current_allocation_ids_cannot_be_reused(self) -> None:
        """Новое распределение не получает ID ни действующей, ни отменённой строки."""
        result = self.replan()
        for identifier in (
            self.rf.second.id,
            self.pf.allocation.id,
            self.replacement.id,
        ):
            with self.subTest(identifier=identifier), self.assertRaises(InventoryError):
                self.replan(
                    result,
                    allocation_ids=(self.replacement.id,),
                    replacements=(replace(self.replacement, id=identifier),),
                )

    def test_replacements_must_be_fresh_and_identity_must_match(self) -> None:
        """Новое намерение не содержит историю и не меняет товар/единицу выбранной строки."""
        released, _ = self.close_b(self.rf.confirm())
        historical = released.allocations[1]
        variants = (
            replace(historical, id=self.replacement.id),
            replace(self.replacement, base_uom=UomCodeVO("KG")),
            replace(
                self.replacement,
                status=FulfillmentAllocationStatus.CANCELLED,
                cancelled_at=self.at,
            ),
            replace(self.rf.confirm().allocations[1], id=self.replacement.id),
        )
        for row in variants:
            with self.subTest(row=row), self.assertRaises(InventoryError):
                self.replan(released, replacements=(row,))

    def test_current_order_demand_split_and_quantity_limits_are_checked(self) -> None:
        """Проверяется весь итоговый состав, а не только сумма новых строк."""
        demand = self.pf.demand
        cases = (
            dict(demand=replace(demand, is_fulfillable=False)),
            dict(
                demand=replace(
                    demand, order_ref=FulfillmentOrderRefVO("orders", "other")
                )
            ),
            dict(demand=replace(demand, lines=(self.pf.other_demand,))),
            dict(
                demand=replace(
                    demand,
                    lines=(
                        replace(self.pf.first_demand, allow_source_split=False),
                        self.pf.other_demand,
                    ),
                )
            ),
            dict(replacements=(self.new_row(self.c, "5"),)),
            dict(
                demand=replace(
                    demand,
                    lines=(
                        replace(
                            self.pf.first_demand, remaining_qty=QuantityVO(Decimal(6))
                        ),
                        self.pf.other_demand,
                    ),
                )
            ),
        )
        for changes in cases:
            with self.subTest(changes=changes), self.assertRaises(InventoryError):
                self.replan(**changes)

    def test_current_item_step_warehouse_activity_and_exact_context_are_checked(
        self,
    ) -> None:
        """Отменённый B не требует текущего контекста, действующие A/C требуют ровно свои снимки."""
        for changes in (
            dict(warehouses=(self.pf.a, replace(self.c, is_active=False))),
            dict(warehouses=(self.c,)),
            dict(warehouses=(self.pf.a, self.c, self.pf.b)),
            dict(warehouses=(self.pf.a, self.c, self.c)),
            dict(inventory_items=()),
            dict(
                inventory_items=(
                    replace(self.pf.item, quantity_rules=QuantityRulesVO(Decimal(2))),
                )
            ),
        ):
            with self.subTest(changes=changes), self.assertRaises(InventoryError):
                self.replan(**changes)

    def test_stale_version_invalid_time_and_repeated_command_are_rejected(self) -> None:
        """Версии без bool, неубывающее время и уникальные новые ID обязательны."""
        for changes in (
            dict(expected_version=True),
            dict(expected_version=self.plan.version - 1),
            dict(updated_at=self.plan.updated_at - timedelta(seconds=1)),
            dict(updated_at=self.at.replace(tzinfo=None)),
        ):
            with self.subTest(changes=changes), self.assertRaises(InventoryError):
                self.replan(**changes)
        result = self.replan(
            updated_at=self.at.astimezone(timezone(timedelta(hours=3)))
        )
        self.assertEqual(result.updated_at, self.at)
        with self.assertRaises(InventoryError):
            self.replan(result, expected_version=self.plan.version)
        with self.assertRaises(InventoryError):
            self.replan(result)

    def test_wrong_plan_statuses_reject_replanning(self) -> None:
        """DRAFT, CONFIRMED, CANCELLED и FULFILLED не открываются для изменения намерений."""
        cancelled = self.plan.cancel(
            expected_version=self.plan.version, updated_at=self.at
        )
        for plan in (self.pf.draft, self.rf.confirm(), cancelled):
            with self.subTest(status=plan.status), self.assertRaises(InventoryError):
                self.replan(plan)

    def test_bad_last_replacement_preserves_entire_original(self) -> None:
        """Ошибка последней строки не оставляет частичной отмены или новой версии."""
        invalid = self.new_row(self.d, "3")
        with self.assertRaises(InventoryError):
            self.replan(
                replacements=(self.replacement, invalid),
                warehouses=(self.pf.a, self.c, self.d),
            )
        self.assertEqual(self.plan.allocations, (self.pf.allocation, self.rf.second))
        self.assertTrue(all(row.cancelled_at is None for row in self.plan.allocations))

    def test_cancelled_entity_is_terminal_and_restore_checks_time_matrix(self) -> None:
        """Отменённая строка требует корректное время и не допускает повторную активацию методами."""
        row = self.replan().allocations[1]
        for changes in (
            dict(cancelled_at=None),
            dict(cancelled_at=self.at.replace(tzinfo=None)),
            dict(status=FulfillmentAllocationStatus.PLANNED),
            dict(fulfilled_qty=QuantityVO(Decimal(1))),
        ):
            with self.subTest(changes=changes), self.assertRaises(InventoryError):
                replace(row, **changes).ensure_valid()
        with self.assertRaises(InventoryError):
            row.confirm_reservation(self.rf.confirm().allocations[1].reservation)
        self.assertIs(row.cancel_unstarted(cancelled_at=self.at), row)
        values = {field.name: getattr(row, field.name) for field in fields(row)}
        values["identifier"] = values.pop("id")
        self.assertEqual(FulfillmentAllocation.restore(**values), row)
        self.assertEqual(
            FulfillmentAllocation.restore(
                **(
                    values
                    | dict(
                        cancelled_at=self.at.astimezone(timezone(timedelta(hours=3)))
                    )
                )
            ),
            row,
        )

    def test_cancellation_cannot_precede_last_reserve_release(self) -> None:
        """Собственная история Entity должна предшествовать терминальной отмене."""
        released, _ = self.close_b(self.rf.confirm())
        row = released.allocations[1]
        with self.assertRaises(InventoryError):
            row.cancel_unstarted(cancelled_at=self.at - timedelta(seconds=1))
        cancelled = self.replan(released).allocations[1]
        with self.assertRaises(InventoryError):
            replace(
                cancelled, cancelled_at=self.at - timedelta(seconds=1)
            ).ensure_valid()

    def test_root_and_snapshot_restore_validate_cancellation_bounds(self) -> None:
        """История не находится вне дат корня; DRAFT не содержит отменённых строк."""
        released, _ = self.close_b(self.rf.confirm())
        result, _ = self.confirm_c(self.replan(released))
        row = result.allocations[1]
        for cancelled_at in (
            self.at + timedelta(seconds=1),
            result.created_at - timedelta(seconds=1),
        ):
            with (
                self.subTest(cancelled_at=cancelled_at),
                self.assertRaises(InventoryError),
            ):
                self.restore(
                    result,
                    allocations=(
                        result.allocations[0],
                        replace(row, cancelled_at=cancelled_at),
                        result.allocations[2],
                    ),
                )
        snapshot = result.shipment_snapshot()
        with self.assertRaises(InventoryError):
            replace(
                snapshot,
                allocations=(
                    snapshot.allocations[0],
                    replace(
                        snapshot.allocations[1],
                        cancelled_at=self.at + timedelta(seconds=1),
                    ),
                    snapshot.allocations[2],
                ),
            ).ensure_valid()
        with self.assertRaises(InventoryError):
            self.restore(self.replan(), status=FulfillmentPlanStatus.DRAFT)

    def test_snapshot_requires_stored_cancellation_time_in_utc(self) -> None:
        """Готовый снимок не нормализует смещение, наивное или сырое значение отмены."""
        released, _ = self.close_b(self.rf.confirm())
        result, _ = self.confirm_c(self.replan(released))
        snapshot = result.shipment_snapshot()
        row = snapshot.allocations[1]
        for value in (
            self.at.astimezone(timezone(timedelta(hours=3))),
            self.at.replace(tzinfo=None),
            "raw",
        ):
            with self.subTest(value=value), self.assertRaises(InventoryError):
                replace(row, cancelled_at=value).ensure_valid()

    def test_root_and_snapshot_keep_history_ids_globally_unique(self) -> None:
        """Историческая строка не исключается из проверки ID распределений и резервов."""
        released, closed = self.close_b(self.rf.confirm())
        result, _ = self.confirm_c(self.replan(released))
        duplicate = replace(result.allocations[2], id=result.allocations[1].id)
        with self.assertRaises(InventoryError):
            self.restore(
                result,
                allocations=(result.allocations[0], result.allocations[1], duplicate),
            )
        current = replace(
            result.allocations[2],
            reservation=replace(
                result.allocations[2].reservation, reservation_id=closed.id
            ),
        )
        with self.assertRaises(InventoryError):
            self.restore(
                result,
                allocations=(result.allocations[0], result.allocations[1], current),
            )
        snapshot = result.shipment_snapshot()
        with self.assertRaises(InventoryError):
            replace(
                snapshot,
                allocations=(
                    snapshot.allocations[0],
                    snapshot.allocations[1],
                    replace(snapshot.allocations[2], id=snapshot.allocations[1].id),
                ),
            ).ensure_valid()

    def test_all_cancelled_is_not_a_valid_active_plan(self) -> None:
        """История сама по себе не заменяет действующий состав зафиксированного плана."""
        rows = tuple(
            row.cancel_unstarted(cancelled_at=self.at) for row in self.plan.allocations
        )
        with self.assertRaises(InventoryError):
            self.restore(self.plan, allocations=rows, updated_at=self.at)

    def test_confirmed_snapshot_requires_active_allocations(self) -> None:
        """Непустая отменённая история не образует обеспеченный состав снимка."""
        released, _ = self.close_b(self.rf.confirm())
        confirmed, _ = self.confirm_c(self.replan(released))
        snapshot = confirmed.shipment_snapshot()
        history_only = tuple(
            row
            for row in snapshot.allocations
            if row.status is FulfillmentAllocationStatus.CANCELLED
        )
        with self.assertRaises(InventoryError):
            replace(snapshot, allocations=history_only).ensure_valid()

    def test_planned_plan_cancellation_keeps_all_replanning_history(self) -> None:
        """Отмена всего PLANNED сохраняет и новые намерения, и отменённые предшественники."""
        result = self.replan()
        cancelled = result.cancel(expected_version=result.version, updated_at=self.at)
        self.assertEqual(cancelled.allocations, result.allocations)
        self.restore(cancelled)

    def test_fractional_replanning_does_not_round_under_small_context(self) -> None:
        """Суммы и остатки сохраняют точность при малой внешней Decimal precision."""
        item = replace(
            self.pf.item,
            base_uom=UomCodeVO("KG"),
            quantity_rules=QuantityRulesVO(Decimal("0.000001")),
        )
        a = replace(
            self.pf.allocation,
            base_uom=item.base_uom,
            quantity=QuantityVO(Decimal("0.123456")),
        )
        b = replace(
            self.rf.second,
            base_uom=item.base_uom,
            quantity=QuantityVO(Decimal("0.654321")),
        )
        plan = self.restore(self.plan, allocations=(a, b))
        demand = replace(
            self.pf.demand,
            lines=(
                replace(
                    self.pf.first_demand,
                    base_uom=item.base_uom,
                    remaining_qty=QuantityVO(Decimal("0.777777")),
                ),
            ),
        )
        new = self.new_row(self.c, "0.654321", inventory_item=item)
        with localcontext() as ctx:
            ctx.prec = 2
            ctx.traps[Inexact] = True
            ctx.traps[Rounded] = True
            result = self.replan(
                plan, replacements=(new,), inventory_items=(item,), demand=demand
            )
            remaining = result.remaining_to_allocate(a.source_ref, demand=demand)
        self.assertEqual(remaining, QuantityVO(Decimal(0)))
        self.assertEqual(result.allocations[-1].quantity, new.quantity)


if __name__ == "__main__":
    unittest.main()
