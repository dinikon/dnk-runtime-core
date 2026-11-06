"""Накопленное исполнение FulfillmentPlan по полным снимкам Shipment и независимая отгрузка складов."""

import unittest
from dataclasses import FrozenInstanceError, fields, replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal, Inexact, Rounded, localcontext
from uuid import uuid4

from test import test_inventory_fulfillment_shipment_domain as shipment_fixture
from src.modules.inventory.domain.error import InventoryError
from src.modules.inventory.domain.fulfillment_plan.aggregate import FulfillmentPlan
from src.modules.inventory.domain.fulfillment_plan.error import (
    FulfillmentDemandExceededError,
    FulfillmentPlanStatusError,
    FulfillmentPlanTimeError,
    FulfillmentPlanVersionConflictError,
    FulfillmentShipmentProgressConflictError,
    FulfillmentShipmentProgressMismatchError,
    InvalidFulfillmentAllocationError,
    InvalidFulfillmentPlanValueError,
    InvalidFulfillmentShipmentProgressRefError,
)
from src.modules.inventory.domain.fulfillment_plan.value_object.allocation_id import (
    FulfillmentAllocationIdVO,
)
from src.modules.inventory.domain.fulfillment_plan.value_object.allocation_status import (
    FulfillmentAllocationStatus,
)
from src.modules.inventory.domain.fulfillment_plan.value_object.identifier import (
    FulfillmentPlanIdVO,
)
from src.modules.inventory.domain.fulfillment_plan.value_object.shipment_progress_ref import (
    FulfillmentShipmentProgressRefVO,
)
from src.modules.inventory.domain.fulfillment_plan.value_object.status import (
    FulfillmentPlanStatus,
)
from src.modules.inventory.domain.inventory_item.value_object.identifier import (
    InventoryItemIdVO,
)
from src.modules.inventory.domain.shipment.aggregate import Shipment
from src.modules.inventory.domain.shipment.error import (
    ShipmentFulfillmentMismatchError,
)
from src.modules.inventory.domain.shipment.fulfillment_snapshot import (
    ShipmentFulfillmentSnapshot,
)
from src.modules.inventory.domain.shipment.registration_snapshot import (
    ShipmentExecutionRegistrationLineSnapshot,
    ShipmentExecutionRegistrationSnapshot,
)
from src.modules.inventory.domain.shipment.value_object.fulfillment_line_binding import (
    FulfillmentShipmentLineBindingVO,
)
from src.modules.inventory.domain.shipment.value_object.identifier import ShipmentIdVO
from src.modules.inventory.domain.shipment.value_object.line_id import ShipmentLineIdVO
from src.modules.inventory.domain.shipment.value_object.order_ref import (
    ShipmentOrderRefVO,
)
from src.modules.inventory.domain.shipment.value_object.status import ShipmentStatus
from src.modules.inventory.domain.stock_execution.value_object.identifier import (
    StockExecutionIdVO,
)
from src.modules.inventory.domain.stock_execution.value_object.line_id import (
    StockExecutionLineIdVO,
)
from src.modules.inventory.domain.stock_posting.value_object.operation_type import (
    StockOperationType,
)
from src.modules.inventory.domain.stock_reservation.value_object.identifier import (
    StockReservationIdVO,
)
from src.modules.inventory.domain.stock_reservation.value_object.source import (
    ReservationSourceVO,
)
from src.modules.inventory.domain.stock_reservation.value_object.status import (
    StockReservationStatus,
)
from src.modules.inventory.domain.value_object.quantity import QuantityVO
from src.modules.inventory.domain.value_object.quantity_rules import QuantityRulesVO
from src.modules.inventory.domain.value_object.stock_owner_id import StockOwnerIdVO
from src.modules.inventory.domain.value_object.uom_code import UomCodeVO
from src.modules.inventory.domain.warehouse.value_object.identifier import WarehouseIdVO


class FulfillmentProgressDomainTests(unittest.TestCase):
    """Проверяет монотонный прогресс, версии, историческое основание и полный состав одного склада."""

    def setUp(self) -> None:
        """Готовит обеспеченный план A=3/B=4, подтверждённый A и созданный до исполнения A черновик B."""
        self.f = shipment_fixture.FulfillmentShipmentDomainTests()
        self.f.setUp()
        self.rf, self.pf = self.f.f, self.f.f.f
        self.plan = self.f.plan
        self.plan, self.a = self.f.assign_and_confirm(self.plan, self.f.create())
        self.b_reservation = self.rf.second_reservation.fulfillment_snapshot()
        self.b_draft = self.f.create(
            warehouse=self.pf.b,
            reservations=(self.b_reservation,),
            line_bindings=(
                FulfillmentShipmentLineBindingVO(
                    self.rf.second.id, ShipmentLineIdVO(uuid4())
                ),
            ),
        )
        self.at = self.f.at + timedelta(minutes=1)
        self.a_partial = self.execute(self.a)

    def execute(
        self,
        shipment: Shipment,
        quantities: dict[ShipmentLineIdVO, str] | None = None,
        *,
        at: datetime | None = None,
    ) -> Shipment:
        """Регистрирует типизированный положительный факт Shipment через его существующий Domain-метод."""
        selected = {shipment.lines[0].id: "1"} if quantities is None else quantities
        occurred = self.at if at is None else at
        registration = ShipmentExecutionRegistrationSnapshot(
            shipment.id,
            shipment.version,
            StockExecutionIdVO(uuid4()),
            StockOperationType.ISSUE,
            shipment.warehouse_id,
            shipment.owner_id,
            occurred,
            tuple(
                ShipmentExecutionRegistrationLineSnapshot(
                    line.id,
                    line.inventory_item_id,
                    line.base_uom,
                    line.reservation_id,
                    QuantityVO(Decimal(selected[line.id])),
                    (StockExecutionLineIdVO(uuid4()),),
                )
                for line in shipment.lines
                if line.id in selected
            ),
        )
        return shipment.register_execution(
            registration, expected_version=shipment.version, updated_at=occurred
        )

    def register(
        self,
        plan: FulfillmentPlan | None = None,
        shipment: Shipment | ShipmentFulfillmentSnapshot | None = None,
        **changes: object,
    ) -> FulfillmentPlan:
        """Передаёт полный снимок факта, текущую версию плана и явное монотонное время регистрации."""
        target = self.plan if plan is None else plan
        source = self.a_partial if shipment is None else shipment
        snapshot = (
            source
            if isinstance(source, ShipmentFulfillmentSnapshot)
            else source.fulfillment_snapshot()
        )
        snapshot.ensure_valid()
        return target.register_shipment(
            snapshot,
            **(
                dict(
                    expected_version=target.version,
                    updated_at=max(target.updated_at, snapshot.updated_at),
                )
                | changes
            ),
        )

    def restore(self, plan: FulfillmentPlan, **changes: object) -> FulfillmentPlan:
        """Восстанавливает весь исторический состав плана без текущих Shipment или резервов."""
        values = {field.name: getattr(plan, field.name) for field in fields(plan)}
        values["identifier"] = values.pop("id")
        return FulfillmentPlan.restore(**(values | changes))

    def confirm_b(
        self, plan: FulfillmentPlan, **changes: object
    ) -> tuple[FulfillmentPlan, Shipment]:
        """Подтверждает прежний черновик B после регистрации A по свежему плану и открытому резерву B."""
        return self.f.assign_and_confirm(
            plan,
            self.b_draft,
            **(
                dict(
                    warehouse=self.pf.b,
                    reservations=(self.b_reservation,),
                    updated_at=plan.updated_at,
                )
                | changes
            ),
        )

    def multi_warehouse_a(self) -> tuple[FulfillmentPlan, Shipment]:
        """Строит A с двумя строками разных оснований и B с одной строкой для проверки нулевого прогресса."""
        extra = self.pf.create_allocation(
            source_ref=self.pf.other_ref, quantity=QuantityVO(Decimal(2))
        )
        planned = self.pf.mark(
            self.pf.add(self.pf.add(self.pf.one, extra), self.rf.second)
        )
        third = self.rf.reserve(extra)
        plan = self.rf.confirm(
            planned,
            bindings=(
                self.rf.first_binding,
                self.rf.second_binding,
                self.rf.binding(extra, third),
            ),
            reservations=(
                self.f.reservation,
                self.b_reservation,
                third.fulfillment_snapshot(),
            ),
        )
        draft = self.f.create(
            fulfillment_plan=plan.shipment_snapshot(),
            reservations=(self.f.reservation, third.fulfillment_snapshot()),
            line_bindings=(
                self.f.binding,
                FulfillmentShipmentLineBindingVO(extra.id, ShipmentLineIdVO(uuid4())),
            ),
        )
        plan, shipment = self.f.assign_and_confirm(
            plan,
            draft,
            reservations=(self.f.reservation, third.fulfillment_snapshot()),
        )
        return plan, self.execute(shipment, {self.f.binding.shipment_line_id: "1"})

    def test_initial_allocations_have_zero_execution_and_computed_remaining(
        self,
    ) -> None:
        """Новый план хранит нулевое исполнение без контрольных точек и без дополнительного счётчика остатка."""
        for allocation in self.plan.allocations:
            self.assertEqual(allocation.fulfilled_qty.value, Decimal(0))
            self.assertIsNone(allocation.shipment_progress)
            self.assertEqual(allocation.remaining_to_fulfill(), allocation.quantity)

    def test_registers_partial_progress_with_one_new_plan_version(self) -> None:
        """Положительный факт A меняет одну Allocation и переводит план в PARTIALLY_FULFILLED одной версией."""
        registered = self.register()
        row = registered.get_allocation(self.pf.allocation.id)
        self.assertEqual(registered.version, self.plan.version + 1)
        self.assertEqual(registered.status, FulfillmentPlanStatus.PARTIALLY_FULFILLED)
        self.assertEqual(row.status, FulfillmentAllocationStatus.PARTIALLY_FULFILLED)
        self.assertEqual(row.fulfilled_qty.value, Decimal(1))
        self.assertEqual(row.remaining_to_fulfill().value, Decimal(2))
        self.assertEqual(row.reservation, self.plan.get_allocation(row.id).reservation)
        self.assertEqual(row.shipment_progress.shipment_id, self.a.id)
        self.assertEqual(row.shipment_progress.shipment_line_id, self.a.lines[0].id)
        self.assertEqual(row.shipment_progress.shipment_version, self.a_partial.version)
        self.assertEqual(
            row.shipment_progress.source_plan_version,
            self.a.fulfillment_source.plan_version,
        )
        self.assertEqual(
            registered.get_allocation(self.rf.second.id),
            self.plan.get_allocation(self.rf.second.id),
        )
        self.assertEqual(self.plan.status, FulfillmentPlanStatus.CONFIRMED)

    def test_cumulative_one_then_three_means_three_and_b_finishes_plan(self) -> None:
        """Последовательность 1→3 не складывается в 4; полное B завершает план без вмешательства в чужие агрегаты."""
        partial = self.register()
        full_a = self.execute(
            self.a_partial, {self.a.lines[0].id: "2"}, at=self.at + timedelta(minutes=1)
        )
        after_a = self.register(partial, full_a)
        self.assertEqual(
            after_a.get_allocation(self.pf.allocation.id).fulfilled_qty.value,
            Decimal(3),
        )
        self.assertEqual(after_a.status, FulfillmentPlanStatus.PARTIALLY_FULFILLED)
        after_a, b = self.confirm_b(after_a)
        full_b = self.execute(
            b, {b.lines[0].id: "4"}, at=after_a.updated_at + timedelta(minutes=1)
        )
        completed = self.register(after_a, full_b)
        self.assertEqual(completed.status, FulfillmentPlanStatus.FULFILLED)
        self.assertEqual(completed.version, self.plan.version + 4)
        self.assertTrue(
            all(
                row.status is FulfillmentAllocationStatus.FULFILLED
                for row in completed.allocations
            )
        )
        self.assertTrue(
            all(
                row.remaining_to_fulfill().value.is_zero()
                for row in completed.allocations
            )
        )
        self.assertIs(self.register(completed, full_b), completed)
        self.assertIs(self.register(completed, full_a), completed)

    def test_exact_replay_is_noop_without_changing_version_or_time(self) -> None:
        """Повтор полного снимка с более поздним временем команды не создаёт второе исполнение или новую версию."""
        registered = self.register()
        repeated = self.register(
            registered, updated_at=registered.updated_at + timedelta(days=1)
        )
        self.assertIs(repeated, registered)
        self.assertEqual(repeated.updated_at, registered.updated_at)

    def test_newer_snapshot_same_quantity_updates_checkpoint_once(self) -> None:
        """Новая версия с тем же прогрессом меняет контрольную точку одной версией, сохраняя количество."""
        registered = self.register()
        newer = replace(
            self.a_partial.fulfillment_snapshot(),
            version=self.a_partial.version + 1,
            updated_at=self.at + timedelta(minutes=1),
        )
        refreshed = self.register(registered, newer)
        row = refreshed.get_allocation(self.pf.allocation.id)
        self.assertEqual(row.fulfilled_qty.value, Decimal(1))
        self.assertEqual(row.shipment_progress.shipment_version, newer.version)
        self.assertEqual(refreshed.version, registered.version + 1)
        self.assertIs(self.register(refreshed, newer), refreshed)

    def test_same_snapshot_version_with_different_quantity_or_time_is_conflict(
        self,
    ) -> None:
        """Одна версия Shipment не может иметь иной прогресс или время обновления."""
        registered = self.register()
        snapshot = self.a_partial.fulfillment_snapshot()
        variants = (
            replace(
                snapshot,
                lines=(replace(snapshot.lines[0], shipped_qty=QuantityVO(Decimal(2))),),
            ),
            replace(snapshot, updated_at=snapshot.updated_at + timedelta(seconds=1)),
        )
        for value in variants:
            with (
                self.subTest(value=value),
                self.assertRaises(FulfillmentShipmentProgressConflictError),
            ):
                self.register(registered, value)

    def test_older_snapshot_version_and_regressing_time_are_rejected(self) -> None:
        """Старые контрольные точки отклоняются даже при прежнем количестве."""
        registered = self.register()
        snap = self.a_partial.fulfillment_snapshot()
        for value in (
            replace(snap, version=snap.version - 1),
            replace(
                snap,
                version=snap.version + 1,
                updated_at=snap.updated_at - timedelta(microseconds=1),
            ),
        ):
            with (
                self.subTest(value=value),
                self.assertRaises(FulfillmentShipmentProgressConflictError),
            ):
                self.register(registered, value)

    def test_more_recent_snapshot_cannot_reduce_cumulative_quantity(self) -> None:
        """Рост версии не разрешает уменьшение ранее принятого исполнения."""
        registered = self.register()
        snap = self.a_partial.fulfillment_snapshot()
        lower = replace(
            snap,
            version=snap.version + 1,
            lines=(replace(snap.lines[0], shipped_qty=QuantityVO(Decimal("0.5"))),),
        )
        with self.assertRaises(FulfillmentShipmentProgressConflictError):
            self.register(registered, lower)

    def test_cannot_rebind_shipment_line_or_original_source_version(self) -> None:
        """После первого факта Allocation принадлежит прежней строке Shipment и её историческому основанию."""
        registered = self.register()
        snapshot = self.a_partial.fulfillment_snapshot()
        variants = (
            replace(snapshot, id=ShipmentIdVO(uuid4())),
            replace(
                snapshot,
                lines=(replace(snapshot.lines[0], id=ShipmentLineIdVO(uuid4())),),
            ),
            replace(
                snapshot,
                fulfillment_source=replace(
                    snapshot.fulfillment_source,
                    plan_version=snapshot.fulfillment_source.plan_version - 1,
                ),
            ),
        )
        for value in variants:
            with (
                self.subTest(value=value),
                self.assertRaises(FulfillmentShipmentProgressMismatchError),
            ):
                self.register(registered, value)

    def test_snapshot_preserves_full_rows_including_zero_and_is_frozen(self) -> None:
        """Частичная отгрузка отдаёт все строки; снимок и вложенные данные неизменяемы."""
        plan, shipment = self.multi_warehouse_a()
        snapshot = shipment.fulfillment_snapshot()
        self.assertEqual(len(snapshot.lines), 2)
        self.assertEqual(
            {row.shipped_qty.value for row in snapshot.lines}, {Decimal(0), Decimal(1)}
        )
        with self.assertRaises(FrozenInstanceError):
            snapshot.version = 99
        with self.assertRaises(FrozenInstanceError):
            snapshot.lines[0].shipped_qty = QuantityVO(Decimal(9))
        registered = self.register(plan, shipment)
        a_rows = [
            row
            for row in registered.allocations
            if row.source.warehouse_id == self.pf.a.id
        ]
        self.assertTrue(
            all(row.shipment_progress.shipment_id == shipment.id for row in a_rows)
        )
        zero = next(row for row in a_rows if row.fulfilled_qty.value.is_zero())
        self.assertEqual(zero.status, FulfillmentAllocationStatus.CONFIRMED)

    def test_zero_row_later_executes_and_all_checkpoint_rows_advance_together(
        self,
    ) -> None:
        """Следующий факт переводит нулевую строку в исполненную и обновляет весь состав Shipment одной версией плана."""
        plan, partial_shipment = self.multi_warehouse_a()
        partial_plan = self.register(plan, partial_shipment)
        remaining = {
            line.id: str(line.remaining_qty().value) for line in partial_shipment.lines
        }
        completed_shipment = self.execute(
            partial_shipment, remaining, at=self.at + timedelta(minutes=1)
        )
        updated = self.register(partial_plan, completed_shipment)
        self.assertEqual(updated.version, partial_plan.version + 1)
        self.assertEqual(updated.status, FulfillmentPlanStatus.PARTIALLY_FULFILLED)
        a_rows = [
            row
            for row in updated.allocations
            if row.source.warehouse_id == self.pf.a.id
        ]
        self.assertTrue(
            all(row.status is FulfillmentAllocationStatus.FULFILLED for row in a_rows)
        )
        self.assertEqual(
            {row.shipment_progress.shipment_version for row in a_rows},
            {completed_shipment.version},
        )
        self.assertEqual(self.restore(updated), updated)
        updated.shipment_snapshot().ensure_valid()

    def test_registration_requires_specialized_shipment_snapshot(self) -> None:
        """Общий снимок исполнения и чужой корень не подменяют контракт происхождения и прогресса Shipment."""
        for value in (
            None,
            object(),
            self.a_partial,
            self.a_partial.execution_snapshot(),
            self.rf.first_reservation.fulfillment_snapshot(),
        ):
            with (
                self.subTest(value=type(value)),
                self.assertRaises(FulfillmentShipmentProgressMismatchError),
            ):
                self.plan.register_shipment(
                    value, expected_version=self.plan.version, updated_at=self.at
                )

    def test_snapshot_missing_zero_row_cannot_register_subset_of_warehouse(
        self,
    ) -> None:
        """Отсутствующая нулевая строка не теряется из обязательного полного состава склада."""
        plan, shipment = self.multi_warehouse_a()
        snapshot = shipment.fulfillment_snapshot()
        subset = replace(
            snapshot,
            lines=tuple(
                row for row in snapshot.lines if not row.shipped_qty.value.is_zero()
            ),
        )
        subset.ensure_valid()
        with self.assertRaises(FulfillmentShipmentProgressMismatchError):
            self.register(plan, subset)

    def test_snapshot_rejects_raw_headers_and_invalid_counter_matrix(self) -> None:
        """Номинальные типы, строгие версии, UTC, уникальность и согласованный статус обязательны."""
        snapshot = self.a_partial.fulfillment_snapshot()
        for change in (
            dict(id=uuid4()),
            dict(version=True),
            dict(version=-1),
            dict(version=Decimal(1)),
            dict(status="PARTIALLY_SHIPPED"),
            dict(status=ShipmentStatus.CONFIRMED),
            dict(status=ShipmentStatus.SHIPPED),
            dict(fulfillment_source=None),
            dict(order_ref=object()),
            dict(updated_at=self.at.replace(tzinfo=None)),
            dict(lines=[]),
            dict(lines=()),
            dict(lines=(object(),)),
            dict(lines=(snapshot.lines[0], snapshot.lines[0])),
        ):
            with self.subTest(change=change), self.assertRaises(InventoryError):
                self.register(shipment=replace(snapshot, **change))
        for change in (
            dict(fulfillment_allocation_id=uuid4()),
            dict(source_ref=object()),
            dict(shipped_qty=QuantityVO(Decimal(4))),
        ):
            with self.subTest(change=change), self.assertRaises(InventoryError):
                replace(snapshot.lines[0], **change).ensure_valid()

    def test_snapshot_getter_rejects_draft_confirmed_cancelled_and_manual_shipment(
        self,
    ) -> None:
        """В план переносится положительный факт производной отгрузки, а не намерение или обычный ручной Shipment."""
        for shipment in (
            self.f.create(),
            self.a,
            self.f.create().cancel(expected_version=0, updated_at=self.f.at),
        ):
            with (
                self.subTest(shipment=shipment),
                self.assertRaises(ShipmentFulfillmentMismatchError),
            ):
                shipment.fulfillment_snapshot()
        manual = self.f.restore(
            self.a_partial,
            fulfillment_source=None,
            lines=tuple(
                replace(row, fulfillment_allocation_id=None)
                for row in self.a_partial.lines
            ),
        )
        with self.assertRaises(ShipmentFulfillmentMismatchError):
            manual.fulfillment_snapshot()

    def test_registration_rejects_wrong_order_plan_owner_or_warehouse(self) -> None:
        """Полный факт обязан относиться к тому же обеспеченному плану, заказу, владельцу и складу."""
        snapshot = self.a_partial.fulfillment_snapshot()
        for change in (
            dict(
                fulfillment_source=replace(
                    snapshot.fulfillment_source, plan_id=FulfillmentPlanIdVO(uuid4())
                )
            ),
            dict(
                fulfillment_source=replace(
                    snapshot.fulfillment_source, plan_version=self.plan.version + 1
                )
            ),
            dict(order_ref=ShipmentOrderRefVO("orders", "42")),
            dict(owner_id=StockOwnerIdVO(uuid4())),
            dict(warehouse_id=WarehouseIdVO(uuid4())),
        ):
            with (
                self.subTest(change=change),
                self.assertRaises(FulfillmentShipmentProgressMismatchError),
            ):
                self.register(shipment=replace(snapshot, **change))

    def test_registration_rejects_changed_line_identity_and_planned_quantity(
        self,
    ) -> None:
        """Ссылка на Allocation не заменяет сверку товара, единицы, резерва, строки заказа и всего плана."""
        snapshot = self.a_partial.fulfillment_snapshot()
        for change in (
            dict(fulfillment_allocation_id=FulfillmentAllocationIdVO(uuid4())),
            dict(source_ref=ReservationSourceVO("orders", "other")),
            dict(reservation_id=StockReservationIdVO(uuid4())),
            dict(inventory_item_id=InventoryItemIdVO(uuid4())),
            dict(base_uom=UomCodeVO("KG")),
            dict(planned_qty=QuantityVO(Decimal(4))),
        ):
            with (
                self.subTest(change=change),
                self.assertRaises(FulfillmentShipmentProgressMismatchError),
            ):
                self.register(
                    shipment=replace(
                        snapshot, lines=(replace(snapshot.lines[0], **change),)
                    )
                )

    def test_registration_requires_confirmed_allocations_strict_version_and_time(
        self,
    ) -> None:
        """DRAFT/PLANNED/CANCELLED не принимают исполнение, версии и время проверяются явно."""
        for plan in (
            self.pf.draft,
            self.rf.plan,
            self.pf.draft.cancel(expected_version=0, updated_at=self.at),
        ):
            with (
                self.subTest(status=plan.status),
                self.assertRaises(FulfillmentPlanStatusError),
            ):
                self.register(plan)
        with self.assertRaises(FulfillmentPlanVersionConflictError):
            self.register(expected_version=self.plan.version + 1)
        with self.assertRaises(InvalidFulfillmentPlanValueError):
            self.register(expected_version=True)
        for at in (
            None,
            self.at.replace(tzinfo=None),
            self.a_partial.updated_at - timedelta(microseconds=1),
        ):
            with self.subTest(at=at), self.assertRaises(FulfillmentPlanTimeError):
                self.register(updated_at=at)
        offset = self.at.astimezone(timezone(timedelta(hours=3)))
        self.assertEqual(self.register(updated_at=offset).updated_at, self.at)

    def test_confirm_b_after_registration_a_preserves_historical_source(self) -> None:
        """Прогресс A меняет версию плана, но прежний черновик B подтверждается по неизменным распределениям и свежему резерву."""
        after_a = self.register()
        self.assertLess(self.b_draft.fulfillment_source.plan_version, after_a.version)
        assigned_b, confirmed_b = self.confirm_b(after_a)
        self.assertEqual(confirmed_b.status, ShipmentStatus.CONFIRMED)
        self.assertEqual(confirmed_b.version, 1)
        self.assertEqual(
            confirmed_b.fulfillment_source, self.b_draft.fulfillment_source
        )
        self.assertEqual(confirmed_b.lines, self.b_draft.lines)
        self.assertEqual(
            after_a.get_allocation(self.rf.second.id).fulfilled_qty.value, Decimal(0)
        )

    def test_confirm_b_after_a_still_rechecks_reservation_and_current_order(
        self,
    ) -> None:
        """Историческая версия основания не ослабляет текущие удержания и лимиты B."""
        after_a = self.register()
        for reservations in (
            (),
            (replace(self.b_reservation, version=self.b_reservation.version + 1),),
            (
                replace(
                    self.b_reservation,
                    reserved_qty=QuantityVO(Decimal(0)),
                    status=StockReservationStatus.RELEASED,
                ),
            ),
        ):
            with (
                self.subTest(reservations=reservations),
                self.assertRaises(InventoryError),
            ):
                self.confirm_b(after_a, reservations=reservations)
        with self.assertRaises(InventoryError):
            self.confirm_b(after_a, order=replace(self.f.order, is_fulfillable=False))
        with self.assertRaises(InventoryError):
            self.confirm_b(
                after_a,
                inventory_items=(
                    replace(self.pf.item, quantity_rules=QuantityRulesVO(Decimal(3))),
                ),
            )

    def test_historical_source_does_not_allow_future_or_changed_selected_allocation(
        self,
    ) -> None:
        """Допуск прежней версии после прогресса A не разрешает будущее основание или изменение B."""
        after_a = self.register()
        future = self.f.restore(
            self.b_draft,
            fulfillment_source=replace(
                self.b_draft.fulfillment_source, plan_version=after_a.version + 1
            ),
        )
        with self.assertRaises(InventoryError):
            self.f.confirm(
                future,
                fulfillment_plan=after_a.shipment_snapshot(),
                warehouse=self.pf.b,
                reservations=(self.b_reservation,),
                updated_at=after_a.updated_at,
            )
        snapshot = after_a.shipment_snapshot()
        changed = replace(
            snapshot,
            allocations=tuple(
                (
                    replace(row, quantity=QuantityVO(Decimal(5)))
                    if row.id == self.rf.second.id
                    else row
                )
                for row in snapshot.allocations
            ),
        )
        with self.assertRaises(ShipmentFulfillmentMismatchError):
            self.confirm_b(after_a, fulfillment_plan=changed)

    def test_new_b_can_be_created_after_full_a_without_loading_consumed_a_reservation(
        self,
    ) -> None:
        """После полного A фабрика B выбирает только ещё не начатый склад и использует текущий остаток заказа."""
        full_a = self.execute(self.a, {self.a.lines[0].id: "3"})
        after_a = self.register(shipment=full_a)
        consumed = self.rf.first_reservation.consume(
            self.rf.first_reservation.requested_qty,
            expected_version=self.rf.first_reservation.version,
            inventory_item=self.pf.item,
            consumed_at=self.at,
            updated_at=self.at,
        )
        self.assertEqual(consumed.status, StockReservationStatus.CONSUMED)
        order = replace(
            self.f.order,
            lines=tuple(
                (
                    replace(row, remaining_to_ship_qty=QuantityVO(Decimal(4)))
                    if row.source_ref == self.pf.line_ref
                    else row
                )
                for row in self.f.order.lines
            ),
        )
        b = self.f.create(
            fulfillment_plan=after_a.shipment_snapshot(),
            warehouse=self.pf.b,
            reservations=(self.b_reservation,),
            created_at=after_a.updated_at,
            line_bindings=(
                FulfillmentShipmentLineBindingVO(
                    self.rf.second.id, ShipmentLineIdVO(uuid4())
                ),
            ),
            order=order,
        )
        self.assertEqual(b.fulfillment_source.plan_version, after_a.version)
        after_a, b = self.f.assign_and_confirm(
            after_a,
            b,
            warehouse=self.pf.b,
            reservations=(self.b_reservation,),
            updated_at=after_a.updated_at,
            order=order,
        )

    def test_started_warehouse_cannot_be_rebuilt_or_confirmed_again(self) -> None:
        """Даже нулевая строка уже зарегистрированного Shipment не становится новым назначением склада."""
        after_a = self.register()
        with self.assertRaises(ShipmentFulfillmentMismatchError):
            self.f.create(
                fulfillment_plan=after_a.shipment_snapshot(),
                created_at=after_a.updated_at,
            )
        second_draft = self.f.create()
        with self.assertRaises(ShipmentFulfillmentMismatchError):
            self.f.confirm(
                second_draft,
                fulfillment_plan=after_a.shipment_snapshot(),
                updated_at=after_a.updated_at,
            )

    def test_remaining_to_allocate_subtracts_only_unfulfilled_commitments(self) -> None:
        """Текущая потребность 6 после отгрузки 1 покрыта остатками A=2/B=4 без повторного вычитания исполненного."""
        registered = self.register()
        demand = replace(
            self.pf.demand,
            lines=tuple(
                (
                    replace(row, remaining_qty=QuantityVO(Decimal(6)))
                    if row.source_ref == self.pf.line_ref
                    else row
                )
                for row in self.pf.demand.lines
            ),
        )
        self.assertEqual(
            registered.remaining_to_allocate(self.pf.line_ref, demand=demand).value,
            Decimal(0),
        )
        smaller = replace(
            demand,
            lines=(
                replace(demand.lines[0], remaining_qty=QuantityVO(Decimal(5))),
                *demand.lines[1:],
            ),
        )
        with self.assertRaises(FulfillmentDemandExceededError):
            registered.remaining_to_allocate(self.pf.line_ref, demand=smaller)

    def test_registration_accepts_existing_fact_without_open_reservation_or_current_settings(
        self,
    ) -> None:
        """Погашение резерва после факта не препятствует исторической регистрации в плане."""
        consumed = self.rf.first_reservation.consume(
            QuantityVO(Decimal(1)),
            expected_version=self.rf.first_reservation.version,
            inventory_item=self.pf.item,
            consumed_at=self.at,
            updated_at=self.at,
        )
        self.assertEqual(consumed.status, StockReservationStatus.PARTIALLY_CONSUMED)
        registered = self.register()
        self.assertEqual(
            registered.get_allocation(self.pf.allocation.id).fulfilled_qty.value,
            Decimal(1),
        )
        self.assertEqual(
            registered.get_allocation(self.pf.allocation.id).reservation.version,
            self.rf.first_reservation.version,
        )

    def test_restore_preserves_partial_and_completed_history_without_current_aggregates(
        self,
    ) -> None:
        """Восстановление сохраняет счётчики и контрольные точки по собственным данным."""
        partial = self.register()
        self.assertEqual(self.restore(partial), partial)
        full_a = self.execute(self.a_partial, {self.a.lines[0].id: "2"})
        after_a = self.register(partial, full_a)
        after_a, b = self.confirm_b(after_a)
        complete = self.register(after_a, self.execute(b, {b.lines[0].id: "4"}))
        self.assertEqual(self.restore(complete), complete)
        with self.assertRaises(FulfillmentPlanStatusError):
            complete.shipment_snapshot()

    def test_restore_rejects_counter_status_matrix_and_lost_progress_reference(
        self,
    ) -> None:
        """Нельзя потерять ссылку факта, завысить количество или восстановить статус без соответствующего исполнения."""
        partial = self.register()
        row = partial.get_allocation(self.pf.allocation.id)
        for change in (
            dict(fulfilled_qty=Decimal(1)),
            dict(fulfilled_qty=QuantityVO(Decimal(4))),
            dict(shipment_progress=None),
            dict(status=FulfillmentAllocationStatus.CONFIRMED),
            dict(status=FulfillmentAllocationStatus.FULFILLED),
            dict(reservation=None),
        ):
            with self.subTest(change=change), self.assertRaises(InventoryError):
                replace(row, **change).ensure_valid()
        for status in (
            FulfillmentPlanStatus.CONFIRMED,
            FulfillmentPlanStatus.PLANNED,
            FulfillmentPlanStatus.FULFILLED,
        ):
            with (
                self.subTest(status=status),
                self.assertRaises(InvalidFulfillmentPlanValueError),
            ):
                self.restore(partial, status=status)

    def test_restore_rejects_partial_checkpoint_group_and_inconsistent_versions(
        self,
    ) -> None:
        """Все строки склада восстанавливаются из одной контрольной точки, включая нулевое исполнение."""
        plan, shipment = self.multi_warehouse_a()
        partial = self.register(plan, shipment)
        zero = next(
            row
            for row in partial.allocations
            if row.source.warehouse_id == self.pf.a.id
            and row.fulfilled_qty.value.is_zero()
        )
        for modified in (
            replace(zero, shipment_progress=None),
            replace(
                zero,
                shipment_progress=replace(
                    zero.shipment_progress,
                    shipment_version=zero.shipment_progress.shipment_version + 1,
                ),
            ),
        ):
            with (
                self.subTest(row=modified),
                self.assertRaises(FulfillmentShipmentProgressMismatchError),
            ):
                self.restore(
                    partial,
                    allocations=tuple(
                        modified if row.id == zero.id else row
                        for row in partial.allocations
                    ),
                )

    def test_restore_rejects_duplicate_shipment_line_and_cross_warehouse_reuse(
        self,
    ) -> None:
        """Связи одной контрольной точки не могут смешивать склады или повторять одну строку Shipment."""
        plan, shipment = self.multi_warehouse_a()
        partial = self.register(plan, shipment)
        a_rows = [
            row
            for row in partial.allocations
            if row.source.warehouse_id == self.pf.a.id
        ]
        changed = replace(
            a_rows[1],
            shipment_progress=replace(
                a_rows[1].shipment_progress,
                shipment_line_id=a_rows[0].shipment_progress.shipment_line_id,
            ),
        )
        with self.assertRaises(InventoryError):
            self.restore(
                partial,
                allocations=tuple(
                    changed if row.id == changed.id else row
                    for row in partial.allocations
                ),
            )
        b = partial.get_allocation(self.rf.second.id)
        changed_b = replace(
            b,
            shipment_progress=replace(
                a_rows[0].shipment_progress, shipment_line_id=ShipmentLineIdVO(uuid4())
            ),
        )
        with self.assertRaises(InventoryError):
            self.restore(
                partial,
                allocations=tuple(
                    changed_b if row.id == b.id else row for row in partial.allocations
                ),
            )

    def test_checkpoint_times_are_inside_plan_history_and_after_reservation_confirmation(
        self,
    ) -> None:
        """Контрольная точка не может ссылаться на будущее состояние или предшествовать подтверждению."""
        partial = self.register()
        row = partial.get_allocation(self.pf.allocation.id)
        for change in (
            dict(shipment_updated_at=partial.updated_at + timedelta(minutes=1)),
            dict(source_plan_version=partial.version),
        ):
            changed = replace(
                row, shipment_progress=replace(row.shipment_progress, **change)
            )
            with (
                self.subTest(change=change),
                self.assertRaises(InventoryError),
            ):
                self.restore(
                    partial,
                    allocations=tuple(
                        changed if old.id == row.id else old
                        for old in partial.allocations
                    ),
                )
        with self.assertRaises(InvalidFulfillmentAllocationError):
            replace(
                row,
                shipment_progress=replace(
                    row.shipment_progress,
                    shipment_updated_at=row.reservation.confirmed_at
                    - timedelta(microseconds=1),
                ),
            ).ensure_valid()

    def test_progress_ref_vo_requires_nominal_ids_strict_versions_and_utc(self) -> None:
        """Контрольная точка immutable и нормализует aware-время без внешних часов."""
        args = dict(
            shipment_id=self.a.id,
            shipment_line_id=self.a.lines[0].id,
            shipment_version=self.a_partial.version,
            shipment_updated_at=self.at,
            source_plan_version=self.plan.version,
        )
        for change in (
            dict(shipment_id=uuid4()),
            dict(shipment_line_id=uuid4()),
            dict(shipment_version=True),
            dict(shipment_version=-1),
            dict(source_plan_version=True),
            dict(source_plan_version=Decimal(1)),
        ):
            with (
                self.subTest(change=change),
                self.assertRaises(InvalidFulfillmentShipmentProgressRefError),
            ):
                FulfillmentShipmentProgressRefVO(**(args | change))
        with self.assertRaises(FulfillmentPlanTimeError):
            FulfillmentShipmentProgressRefVO(
                **(args | dict(shipment_updated_at=self.at.replace(tzinfo=None)))
            )
        ref = FulfillmentShipmentProgressRefVO(
            **(
                args
                | dict(
                    shipment_updated_at=self.at.astimezone(timezone(timedelta(hours=3)))
                )
            )
        )
        self.assertEqual(ref.shipment_updated_at, self.at)
        with self.assertRaises(FrozenInstanceError):
            ref.shipment_version = 9

    def test_failure_after_valid_first_row_leaves_entire_plan_unchanged(self) -> None:
        """Ошибка последней строки не сохраняет частичную регистрацию ни одного распределения."""
        plan, shipment = self.multi_warehouse_a()
        registered = self.register(plan, shipment)
        snapshot = shipment.fulfillment_snapshot()
        by_id = {row.fulfillment_allocation_id: row for row in snapshot.lines}
        first, last = [
            by_id[row.id] for row in registered.allocations if row.id in by_id
        ]
        changed = replace(
            snapshot,
            version=snapshot.version + 1,
            lines=(
                first,
                replace(last, id=ShipmentLineIdVO(uuid4())),
            ),
        )
        before = registered.allocations
        with self.assertRaises(FulfillmentShipmentProgressMismatchError):
            self.register(registered, changed)
        self.assertEqual(registered.allocations, before)
        self.assertEqual(registered.version, plan.version + 1)

    def test_registration_after_other_warehouse_preserves_previously_registered_checkpoint(
        self,
    ) -> None:
        """Обновление B не переписывает уже принятую контрольную точку A."""
        after_a = self.register()
        a_ref = after_a.get_allocation(self.pf.allocation.id).shipment_progress
        after_a, b = self.confirm_b(after_a)
        b_partial = self.execute(b, {b.lines[0].id: "2"})
        after_b = self.register(after_a, b_partial)
        self.assertEqual(
            after_b.get_allocation(self.pf.allocation.id).shipment_progress, a_ref
        )
        self.assertEqual(
            after_b.get_allocation(self.rf.second.id).fulfilled_qty.value, Decimal(2)
        )
        self.assertIs(self.register(after_b, self.a_partial), after_b)

    def test_fractional_progress_and_remaining_are_exact_under_small_decimal_context(
        self,
    ) -> None:
        """Весовые количества 0.15→3.25 не округляются при регистрации и вычислении остатка."""
        item = replace(
            self.pf.item,
            base_uom=UomCodeVO("KG"),
            quantity_rules=QuantityRulesVO(Decimal("0.05")),
        )
        self.pf.item = item
        self.pf.demand = replace(
            self.pf.demand,
            lines=tuple(
                replace(row, base_uom=item.base_uom) for row in self.pf.demand.lines
            ),
        )
        a = self.pf.create_allocation(quantity=QuantityVO(Decimal("3.25")))
        b = self.pf.create_allocation(
            source=self.rf.second.source, quantity=QuantityVO(Decimal("3.75"))
        )
        planned = self.pf.mark(self.pf.add(self.pf.add(self.pf.draft, a), b))
        a_res, b_res = self.rf.reserve(a), self.rf.reserve(b)
        plan = self.rf.confirm(
            planned,
            bindings=(self.rf.binding(a, a_res), self.rf.binding(b, b_res)),
            reservations=(a_res.fulfillment_snapshot(), b_res.fulfillment_snapshot()),
        )
        order = replace(
            self.f.order,
            lines=tuple(
                replace(row, base_uom=item.base_uom) for row in self.f.order.lines
            ),
        )
        draft = self.f.create(
            fulfillment_plan=plan.shipment_snapshot(),
            reservations=(a_res.fulfillment_snapshot(),),
            line_bindings=(
                FulfillmentShipmentLineBindingVO(a.id, ShipmentLineIdVO(uuid4())),
            ),
            order=order,
        )
        plan, shipment = self.f.assign_and_confirm(
            plan,
            draft,
            reservations=(a_res.fulfillment_snapshot(),),
            order=order,
        )
        first = self.execute(shipment, {shipment.lines[0].id: "0.15"})
        last = self.execute(first, {shipment.lines[0].id: "3.10"})
        with localcontext() as context:
            context.prec = 1
            context.traps[Inexact] = True
            context.traps[Rounded] = True
            partial = self.register(plan, first)
            self.assertEqual(
                partial.get_allocation(a.id).remaining_to_fulfill().value,
                Decimal("3.10"),
            )
            full = self.register(partial, last)
            self.assertEqual(
                full.get_allocation(a.id).fulfilled_qty.value, Decimal("3.25")
            )
            self.assertEqual(
                full.get_allocation(a.id).remaining_to_fulfill().value, Decimal(0)
            )


if __name__ == "__main__":
    unittest.main()
