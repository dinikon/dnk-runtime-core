"""Назначение производного Shipment до подтверждения, защита от дублей и снятие после отмены черновика."""

import unittest
from dataclasses import FrozenInstanceError, fields, replace
from datetime import timedelta, timezone
from decimal import Decimal
from uuid import uuid4

from test import test_inventory_fulfillment_shipment_domain as fixtures
from src.modules.inventory.domain.error import InventoryError
from src.modules.inventory.domain.fulfillment_plan.aggregate import FulfillmentPlan
from src.modules.inventory.domain.fulfillment_plan.error import (
    FulfillmentShipmentAssignmentConflictError,
    InvalidFulfillmentShipmentAssignmentError,
    FulfillmentPlanTimeError,
    FulfillmentPlanVersionConflictError,
    FulfillmentPlanStatusError,
    FulfillmentShipmentProgressMismatchError,
)
from src.modules.inventory.domain.fulfillment_plan.value_object.shipment_assignment import (
    FulfillmentShipmentAssignmentRefVO,
)
from src.modules.inventory.domain.fulfillment_plan.value_object.status import (
    FulfillmentPlanStatus,
)
from src.modules.inventory.domain.shipment.aggregate import Shipment
from src.modules.inventory.domain.shipment.error import ShipmentFulfillmentMismatchError
from src.modules.inventory.domain.shipment.registration_snapshot import (
    ShipmentExecutionRegistrationSnapshot,
    ShipmentExecutionRegistrationLineSnapshot,
)
from src.modules.inventory.domain.shipment.value_object.identifier import ShipmentIdVO
from src.modules.inventory.domain.shipment.value_object.line_id import ShipmentLineIdVO
from src.modules.inventory.domain.shipment.value_object.fulfillment_line_binding import (
    FulfillmentShipmentLineBindingVO,
)
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
from src.modules.inventory.domain.value_object.quantity import QuantityVO
from src.modules.inventory.domain.value_object.stock_owner_id import StockOwnerIdVO


class ShipmentAssignmentDomainTests(unittest.TestCase):
    """Проверяет полный жизненный цикл назначения и независимость резервов и исполнения."""

    def setUp(self) -> None:
        """Готовит реальный обеспеченный план и черновик A; исходный план остаётся без назначения."""
        self.f = fixtures.FulfillmentShipmentDomainTests()
        self.f.setUp()
        self.plan = self.f.plan
        self.draft = self.f.create()
        self.at = self.f.at
        self.assigned = self.assign()
        self.cancelled = self.draft.cancel(expected_version=0, updated_at=self.at)

    def assign(
        self,
        plan: FulfillmentPlan | None = None,
        shipment: Shipment | None = None,
        **changes: object,
    ) -> FulfillmentPlan:
        """Передаёт реальный снимок черновика и текущую версию изменяемого плана."""
        target = self.plan if plan is None else plan
        source = self.draft if shipment is None else shipment
        return target.assign_shipment(
            source.assignment_snapshot(),
            **(dict(expected_version=target.version, updated_at=self.at) | changes),
        )

    def confirm(
        self,
        plan: FulfillmentPlan | None = None,
        shipment: Shipment | None = None,
        **changes: object,
    ) -> Shipment:
        """Вызывает подтверждение напрямую без автоматического назначения в тестовом helper."""
        target = self.assigned if plan is None else plan
        source = self.draft if shipment is None else shipment
        return source.confirm_from_fulfillment_plan(
            **(
                dict(
                    expected_version=source.version,
                    fulfillment_plan=target.shipment_snapshot(),
                    warehouse=self.f.f.f.a,
                    order=self.f.order,
                    inventory_items=(self.f.f.f.item,),
                    reservations=(self.f.reservation,),
                    updated_at=self.at,
                )
                | changes
            )
        )

    def release(
        self, plan: FulfillmentPlan | None = None, **changes: object
    ) -> FulfillmentPlan:
        """Передаёт отменённый производный черновик для снятия полного назначения склада."""
        target = self.assigned if plan is None else plan
        return target.release_shipment_assignment(
            self.cancelled.assignment_snapshot(),
            **(dict(expected_version=target.version, updated_at=self.at) | changes),
        )

    def restore(self, plan: FulfillmentPlan, **changes: object) -> FulfillmentPlan:
        """Восстанавливает весь собственный состав без чтения Shipment или текущих резервов."""
        values = {field.name: getattr(plan, field.name) for field in fields(plan)}
        values["identifier"] = values.pop("id")
        return FulfillmentPlan.restore(**(values | changes))

    def execute(self, shipment: Shipment) -> Shipment:
        """Регистрирует заданный положительный факт через существующий метод отправления."""
        line = shipment.lines[0]
        registration = ShipmentExecutionRegistrationSnapshot(
            shipment.id,
            shipment.version,
            StockExecutionIdVO(uuid4()),
            StockOperationType.ISSUE,
            shipment.warehouse_id,
            shipment.owner_id,
            self.at,
            (
                ShipmentExecutionRegistrationLineSnapshot(
                    line.id,
                    line.inventory_item_id,
                    line.base_uom,
                    line.reservation_id,
                    QuantityVO(Decimal(1)),
                    (StockExecutionLineIdVO(uuid4()),),
                ),
            ),
        )
        return shipment.register_execution(
            registration, expected_version=shipment.version, updated_at=self.at
        )

    def multi(self) -> tuple[FulfillmentPlan, Shipment]:
        """Готовит полный состав A с двумя строками для проверки групповых инвариантов."""
        rf, pf = self.f.f, self.f.f.f
        extra = pf.create_allocation(
            source_ref=pf.other_ref, quantity=QuantityVO(Decimal(2))
        )
        planned = pf.mark(pf.add(pf.add(pf.one, extra), rf.second))
        reserve = rf.reserve(extra)
        plan = rf.confirm(
            planned,
            bindings=(rf.first_binding, rf.second_binding, rf.binding(extra, reserve)),
            reservations=(
                self.f.reservation,
                rf.second_reservation.fulfillment_snapshot(),
                reserve.fulfillment_snapshot(),
            ),
        )
        draft = self.f.create(
            fulfillment_plan=plan.shipment_snapshot(),
            reservations=(self.f.reservation, reserve.fulfillment_snapshot()),
            line_bindings=(
                self.f.binding,
                FulfillmentShipmentLineBindingVO(extra.id, ShipmentLineIdVO(uuid4())),
            ),
        )
        return plan, draft

    def test_assignment_is_one_version_without_execution_or_reservation_changes(
        self,
    ) -> None:
        """Назначение меняет только план и связь, сохраняя статус, количество и историческое подтверждение."""
        self.assertEqual(self.assigned.version, self.plan.version + 1)
        self.assertEqual(self.assigned.status, self.plan.status)
        self.assertTrue(self.assigned.is_fully_confirmed())
        original = self.plan.get_allocation(self.f.binding.allocation_id)
        row = self.assigned.get_allocation(original.id)
        self.assertIsNone(original.shipment_assignment)
        self.assertIsNone(row.shipment_progress)
        self.assertEqual(row.fulfilled_qty.value, Decimal(0))
        self.assertEqual(row.reservation, original.reservation)
        self.assertEqual(row.shipment_assignment.shipment_id, self.draft.id)
        self.assertEqual(row.shipment_assignment.shipment_version, self.draft.version)
        self.assertEqual(
            row.shipment_assignment.source_plan_version,
            self.draft.fulfillment_source.plan_version,
        )
        self.assertEqual(
            self.f.f.first_reservation.fulfillment_snapshot(), self.f.reservation
        )

    def test_repeat_preserves_first_assigned_at_and_returns_same_plan(self) -> None:
        """Повтор того же черновика не создаёт версию и не переписывает первое время назначения."""
        self.assertIs(
            self.assign(self.assigned, updated_at=self.at + timedelta(days=1)),
            self.assigned,
        )

    def test_second_shipment_cannot_claim_same_allocation_and_reservation(self) -> None:
        """Два разных отправления на то же распределение больше не назначаются последовательно в одном плане."""
        other = self.f.create()
        self.assertNotEqual(other.id, self.draft.id)
        with self.assertRaises(FulfillmentShipmentAssignmentConflictError):
            self.assign(self.assigned, other)

    def test_factory_blocks_assigned_warehouse_and_allows_other_warehouse(self) -> None:
        """Назначение A блокирует новый A, сохраняя возможность создать B."""
        with self.assertRaises(ShipmentFulfillmentMismatchError):
            self.f.create(fulfillment_plan=self.assigned.shipment_snapshot())
        b = self.f.create(
            fulfillment_plan=self.assigned.shipment_snapshot(),
            warehouse=self.f.f.f.b,
            reservations=(self.f.f.second_reservation.fulfillment_snapshot(),),
            line_bindings=(
                FulfillmentShipmentLineBindingVO(
                    self.f.f.second.id, ShipmentLineIdVO(uuid4())
                ),
            ),
        )
        self.assertEqual(b.status, ShipmentStatus.DRAFT)

    def test_confirmation_requires_prior_assignment_to_exact_shipment(self) -> None:
        """Подтверждение без назначения и по назначению другого ID/строки запрещено."""
        with self.assertRaises(ShipmentFulfillmentMismatchError):
            self.confirm(self.plan)
        with self.assertRaises(ShipmentFulfillmentMismatchError):
            self.confirm(shipment=self.f.create())
        changed = self.f.restore(
            self.draft,
            lines=(replace(self.draft.lines[0], id=ShipmentLineIdVO(uuid4())),),
        )
        with self.assertRaises(ShipmentFulfillmentMismatchError):
            self.confirm(shipment=changed)

    def test_confirmation_preserves_older_origin_after_assignment(self) -> None:
        """Назначение увеличивает версию плана, а подтверждение сохраняет прежний источник черновика."""
        confirmed = self.confirm()
        self.assertEqual(confirmed.status, ShipmentStatus.CONFIRMED)
        self.assertLess(
            confirmed.fulfillment_source.plan_version, self.assigned.version
        )
        self.assertEqual(confirmed.fulfillment_source, self.draft.fulfillment_source)

    def test_confirmation_rechecks_live_reservation_after_assignment(self) -> None:
        """Назначение само не делает устаревшее или истёкшее удержание пригодным для подтверждения."""
        with self.assertRaises(InventoryError):
            self.confirm(
                reservations=(
                    replace(self.f.reservation, version=self.f.reservation.version + 1),
                )
            )
        with self.assertRaises(InventoryError):
            self.confirm(updated_at=self.f.reservation.expires_at)

    def test_registered_progress_requires_and_preserves_assignment(self) -> None:
        """Положительный факт без назначения отвергается, а назначенный факт сохраняет связь и контрольную точку."""
        fact = self.execute(self.confirm())
        with self.assertRaises(FulfillmentShipmentProgressMismatchError):
            self.plan.register_shipment(
                fact.fulfillment_snapshot(),
                expected_version=self.plan.version,
                updated_at=self.at,
            )
        registered = self.assigned.register_shipment(
            fact.fulfillment_snapshot(),
            expected_version=self.assigned.version,
            updated_at=self.at,
        )
        row = registered.get_allocation(self.f.binding.allocation_id)
        self.assertEqual(
            row.shipment_assignment,
            self.assigned.get_allocation(row.id).shipment_assignment,
        )
        self.assertEqual(
            row.shipment_progress.shipment_id, row.shipment_assignment.shipment_id
        )
        self.assertEqual(self.restore(registered), registered)
        self.assertIs(
            registered.register_shipment(
                fact.fulfillment_snapshot(),
                expected_version=registered.version,
                updated_at=self.at,
            ),
            registered,
        )

    def test_cancelled_draft_releases_assignment_but_keeps_reservation_and_status(
        self,
    ) -> None:
        """Отмена и снятие возвращают склад к новому назначению без освобождения товарного резерва."""
        released = self.release()
        row = released.get_allocation(self.f.binding.allocation_id)
        self.assertIsNone(row.shipment_assignment)
        self.assertEqual(
            row.reservation, self.assigned.get_allocation(row.id).reservation
        )
        self.assertEqual(released.status, self.assigned.status)
        self.assertEqual(released.version, self.assigned.version + 1)
        new = self.f.create(fulfillment_plan=released.shipment_snapshot())
        reassigned = released.assign_shipment(
            new.assignment_snapshot(),
            expected_version=released.version,
            updated_at=self.at,
        )
        self.assertEqual(
            reassigned.get_allocation(row.id).shipment_assignment.shipment_id, new.id
        )

    def test_release_requires_cancelled_and_newer_shipment_version(self) -> None:
        """Живой черновик и отмена со старой версией не снимают назначение."""
        with self.assertRaises(FulfillmentShipmentAssignmentConflictError):
            self.assigned.release_shipment_assignment(
                self.draft.assignment_snapshot(),
                expected_version=self.assigned.version,
                updated_at=self.at,
            )
        cancelled = replace(
            self.cancelled.assignment_snapshot(), version=self.draft.version
        )
        with self.assertRaises(FulfillmentShipmentAssignmentConflictError):
            self.assigned.release_shipment_assignment(
                cancelled, expected_version=self.assigned.version, updated_at=self.at
            )

    def test_repeated_release_is_noop_but_old_cancel_cannot_clear_new_assignment(
        self,
    ) -> None:
        """Повтор отмены при пустом назначении безопасен, а после нового назначения старый снимок отклоняется."""
        released = self.release()
        self.assertIs(
            self.release(released, updated_at=self.at + timedelta(days=1)), released
        )
        new = self.f.create(fulfillment_plan=released.shipment_snapshot())
        assigned = self.assign(released, new)
        with self.assertRaises(FulfillmentShipmentAssignmentConflictError):
            self.release(assigned)

    def test_late_cancel_cannot_clear_started_assignment(self) -> None:
        """Старый снимок отмены не снимает назначение после принятого исполнения."""
        fact = self.execute(self.confirm())
        registered = self.assigned.register_shipment(
            fact.fulfillment_snapshot(),
            expected_version=self.assigned.version,
            updated_at=self.at,
        )
        with self.assertRaises(FulfillmentShipmentAssignmentConflictError):
            self.release(registered)
        with self.assertRaises(ShipmentFulfillmentMismatchError):
            self.confirm().assignment_snapshot()

    def test_assignment_snapshot_is_complete_frozen_and_zero_progress(self) -> None:
        """Черновик и его отмена дают полный immutable-контракт; частичный факт не выдаётся как назначение."""
        draft = self.draft.assignment_snapshot()
        cancelled = self.cancelled.assignment_snapshot()
        self.assertEqual(draft.lines, cancelled.lines)
        self.assertGreater(cancelled.version, draft.version)
        with self.assertRaises(FrozenInstanceError):
            draft.version = 9
        with self.assertRaises(FrozenInstanceError):
            draft.lines[0].shipped_qty = QuantityVO(Decimal(1))
        with self.assertRaises(InventoryError):
            replace(draft.lines[0], shipped_qty=QuantityVO(Decimal(1))).ensure_valid()
        with self.assertRaises(ShipmentFulfillmentMismatchError):
            self.execute(self.confirm()).assignment_snapshot()

    def test_snapshot_rejects_invalid_headers_rows_and_duplicates(self) -> None:
        """Снимок проверяет номинальные значения, строгую версию, UTC и уникальные ссылки."""
        snapshot = self.draft.assignment_snapshot()
        for change in (
            dict(id=uuid4()),
            dict(version=True),
            dict(version=-1),
            dict(status="DRAFT"),
            dict(status=ShipmentStatus.CONFIRMED),
            dict(fulfillment_source=None),
            dict(order_ref=object()),
            dict(updated_at=self.at.replace(tzinfo=None)),
            dict(lines=[]),
            dict(lines=()),
            dict(lines=(object(),)),
            dict(lines=(snapshot.lines[0], snapshot.lines[0])),
        ):
            with self.subTest(change=change), self.assertRaises(InventoryError):
                replace(snapshot, **change).ensure_valid()

    def test_assign_requires_specialized_current_snapshot(self) -> None:
        """Чужой корень или другой контракт не подменяет специализированное основание назначения."""
        for value in (None, object(), self.draft, self.draft.execution_snapshot()):
            with (
                self.subTest(value=type(value)),
                self.assertRaises(FulfillmentShipmentAssignmentConflictError),
            ):
                self.plan.assign_shipment(
                    value, expected_version=self.plan.version, updated_at=self.at
                )

    def test_assignment_rejects_wrong_owner_order_origin_and_quantity(self) -> None:
        """Назначение сверяет полный собственный состав плана и не принимает будущее основание."""
        snapshot = self.draft.assignment_snapshot()
        for change in (
            dict(owner_id=StockOwnerIdVO(uuid4())),
            dict(order_ref=ShipmentOrderRefVO("orders", "other")),
            dict(
                fulfillment_source=replace(
                    snapshot.fulfillment_source, plan_version=self.plan.version + 1
                )
            ),
            dict(
                lines=(replace(snapshot.lines[0], planned_qty=QuantityVO(Decimal(4))),)
            ),
            dict(
                lines=(
                    replace(
                        snapshot.lines[0], reservation_id=StockReservationIdVO(uuid4())
                    ),
                )
            ),
        ):
            with (
                self.subTest(change=change),
                self.assertRaises(FulfillmentShipmentAssignmentConflictError),
            ):
                self.plan.assign_shipment(
                    replace(snapshot, **change),
                    expected_version=self.plan.version,
                    updated_at=self.at,
                )

    def test_selected_group_assignment_and_release_are_one_transition(self) -> None:
        """Выбранная группа назначается/снимается одной версией; до назначения можно выбрать поднабор."""
        plan, draft = self.multi()
        snapshot = draft.assignment_snapshot()
        subset = replace(
            draft.assignment_snapshot(), lines=(draft.assignment_snapshot().lines[0],)
        )
        partial = plan.assign_shipment(
            subset, expected_version=plan.version, updated_at=self.at
        )
        self.assertEqual(
            sum(row.shipment_assignment is not None for row in partial.allocations), 1
        )
        assigned = plan.assign_shipment(
            snapshot, expected_version=plan.version, updated_at=self.at
        )
        rows = [
            row
            for row in assigned.allocations
            if row.source.warehouse_id == draft.warehouse_id
        ]
        self.assertEqual(len(rows), 2)
        self.assertEqual(
            {row.shipment_assignment.assigned_at for row in rows}, {self.at}
        )
        cancelled = draft.cancel(expected_version=draft.version, updated_at=self.at)
        released = assigned.release_shipment_assignment(
            cancelled.assignment_snapshot(),
            expected_version=assigned.version,
            updated_at=self.at,
        )
        self.assertEqual(released.version, assigned.version + 1)
        self.assertTrue(
            all(row.shipment_assignment is None for row in released.allocations)
        )

    def test_restore_accepts_free_neighbors_but_rejects_duplicate_assignment_line(
        self,
    ) -> None:
        """Свободная соседняя строка допустима; повтор строки внутри одного Shipment запрещён."""
        plan, draft = self.multi()
        assigned = plan.assign_shipment(
            draft.assignment_snapshot(),
            expected_version=plan.version,
            updated_at=self.at,
        )
        rows = [
            row for row in assigned.allocations if row.shipment_assignment is not None
        ]
        free_neighbor = replace(rows[1], shipment_assignment=None)
        partial = self.restore(
            assigned,
            allocations=tuple(
                free_neighbor if row.id == free_neighbor.id else row
                for row in assigned.allocations
            ),
        )
        partial.shipment_snapshot().ensure_valid()
        for modified in (
            replace(
                rows[1],
                shipment_assignment=replace(
                    rows[1].shipment_assignment,
                    shipment_line_id=rows[0].shipment_assignment.shipment_line_id,
                ),
            ),
        ):
            with self.subTest(row=modified), self.assertRaises(InventoryError):
                self.restore(
                    assigned,
                    allocations=tuple(
                        modified if row.id == modified.id else row
                        for row in assigned.allocations
                    ),
                )

    def test_restore_rejects_assignment_time_and_future_source_version(self) -> None:
        """Назначение находится внутри истории корня и ссылается на более раннюю версию основания."""
        row = self.assigned.get_allocation(self.f.binding.allocation_id)
        for change in (
            dict(assigned_at=self.at + timedelta(minutes=1)),
            dict(source_plan_version=self.assigned.version),
        ):
            modified = replace(
                row, shipment_assignment=replace(row.shipment_assignment, **change)
            )
            with self.subTest(change=change), self.assertRaises(InventoryError):
                self.restore(
                    self.assigned,
                    allocations=tuple(
                        modified if old.id == row.id else old
                        for old in self.assigned.allocations
                    ),
                )
        self.assertEqual(self.restore(self.assigned), self.assigned)

    def test_progress_restore_cannot_drop_or_change_assignment(self) -> None:
        """Контрольная точка исполнения сохраняет соответствующее назначение."""
        fact = self.execute(self.confirm())
        registered = self.assigned.register_shipment(
            fact.fulfillment_snapshot(),
            expected_version=self.assigned.version,
            updated_at=self.at,
        )
        row = registered.get_allocation(self.f.binding.allocation_id)
        for assignment in (
            None,
            replace(row.shipment_assignment, shipment_id=ShipmentIdVO(uuid4())),
        ):
            with self.subTest(assignment=assignment), self.assertRaises(InventoryError):
                replace(row, shipment_assignment=assignment).ensure_valid()

    def test_strict_versions_and_explicit_monotonic_time(self) -> None:
        """Версии bool/устаревшие и время до состояния черновика запрещены."""
        with self.assertRaises(FulfillmentPlanVersionConflictError):
            self.assign(expected_version=self.plan.version + 1)
        with self.assertRaises(InventoryError):
            self.assign(expected_version=True)
        with self.assertRaises(FulfillmentPlanTimeError):
            self.assign(updated_at=self.at - timedelta(microseconds=1))
        with self.assertRaises(FulfillmentPlanTimeError):
            self.assign(updated_at=self.at.replace(tzinfo=None))
        offset = self.at.astimezone(timezone(timedelta(hours=3)))
        self.assertEqual(self.assign(updated_at=offset).updated_at, self.at)

    def test_lifecycle_and_manual_shipment_boundaries(self) -> None:
        """План без подтверждений и ручные отправления не участвуют в назначениях Fulfillment."""
        for plan in (self.f.f.f.draft, self.f.f.plan):
            with (
                self.subTest(plan=plan.status),
                self.assertRaises(FulfillmentPlanStatusError),
            ):
                self.assign(plan)
        manual = Shipment.create(
            identifier=ShipmentIdVO(uuid4()),
            order_ref=self.f.order.order_ref,
            warehouse=self.f.f.f.a,
            owner_id=self.plan.owner_id,
            created_at=self.at,
        )
        with self.assertRaises(ShipmentFulfillmentMismatchError):
            manual.assignment_snapshot()
        with self.assertRaises(FulfillmentShipmentAssignmentConflictError):
            self.assign(shipment=self.cancelled)

    def test_partial_plan_assignment_and_other_warehouse_confirmation_preserve_links(
        self,
    ) -> None:
        """A назначается при ожидающем B; подтверждение B не обесценивает назначенный A."""
        partial = self.f.f.partial()
        draft = self.f.create(fulfillment_plan=partial.shipment_snapshot())
        assigned = self.assign(partial, draft)
        self.assertEqual(assigned.status, FulfillmentPlanStatus.PARTIALLY_CONFIRMED)
        self.assertFalse(assigned.is_fully_confirmed())
        covered = self.f.f.finish(assigned, updated_at=self.at)
        confirmed = self.confirm(covered, draft)
        self.assertEqual(confirmed.fulfillment_source, draft.fulfillment_source)
        self.assertEqual(
            covered.get_allocation(self.f.binding.allocation_id).shipment_assignment,
            assigned.get_allocation(self.f.binding.allocation_id).shipment_assignment,
        )

    def test_assignment_vo_is_frozen_and_rejects_raw_ids_and_versions(self) -> None:
        """VO проверяет собственные ссылки, строгие версии и aware-время."""
        args = dict(
            shipment_id=self.draft.id,
            shipment_line_id=self.draft.lines[0].id,
            shipment_version=0,
            source_plan_version=self.plan.version,
            assigned_at=self.at,
        )
        for change in (
            dict(shipment_id=uuid4()),
            dict(shipment_line_id=uuid4()),
            dict(shipment_version=True),
            dict(shipment_version=-1),
            dict(source_plan_version=Decimal(1)),
        ):
            with (
                self.subTest(change=change),
                self.assertRaises(InvalidFulfillmentShipmentAssignmentError),
            ):
                FulfillmentShipmentAssignmentRefVO(**(args | change))
        with self.assertRaises(FulfillmentPlanTimeError):
            FulfillmentShipmentAssignmentRefVO(
                **(args | dict(assigned_at=self.at.replace(tzinfo=None)))
            )
        ref = FulfillmentShipmentAssignmentRefVO(**args)
        with self.assertRaises(FrozenInstanceError):
            ref.shipment_version = 1

    def test_failed_claim_and_release_leave_originals_unchanged(self) -> None:
        """Конфликт не сохраняет часть назначений и не меняет ни план, ни черновики, ни резервы."""
        before = (self.assigned, self.draft, self.cancelled, self.f.f.first_reservation)
        with self.assertRaises(FulfillmentShipmentAssignmentConflictError):
            self.assign(self.assigned, self.f.create())
        with self.assertRaises(FulfillmentShipmentAssignmentConflictError):
            self.assigned.release_shipment_assignment(
                self.draft.assignment_snapshot(),
                expected_version=self.assigned.version,
                updated_at=self.at,
            )
        self.assertEqual(
            before,
            (self.assigned, self.draft, self.cancelled, self.f.f.first_reservation),
        )


if __name__ == "__main__":
    unittest.main()
