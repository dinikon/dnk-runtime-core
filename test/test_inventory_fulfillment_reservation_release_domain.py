"""Снятие подтверждений по явно закрытым резервам с историей и безопасной заменой."""

import unittest
from dataclasses import FrozenInstanceError, fields, replace
from datetime import timedelta, timezone
from decimal import Decimal, localcontext, Inexact, Rounded
from uuid import uuid4

from test import test_inventory_fulfillment_reservation_domain as reservation_fixture
from test import test_inventory_fulfillment_shipment_domain as shipment_fixture
from test import test_inventory_fulfillment_progress_domain as progress_fixture
from test import test_inventory_shipment_assignment_domain as assignment_fixture
from src.modules.inventory.domain.error import InventoryError
from src.modules.inventory.domain.fulfillment_plan.aggregate import FulfillmentPlan
from src.modules.inventory.domain.fulfillment_plan.entity.fulfillment_allocation import (
    FulfillmentAllocation,
)
from src.modules.inventory.domain.fulfillment_plan.value_object.allocation_status import (
    FulfillmentAllocationStatus,
)
from src.modules.inventory.domain.fulfillment_plan.value_object.reservation_binding import (
    FulfillmentReservationBindingVO,
)
from src.modules.inventory.domain.fulfillment_plan.value_object.reservation_ref import (
    FulfillmentReservationRefVO,
)
from src.modules.inventory.domain.fulfillment_plan.value_object.reservation_release import (
    FulfillmentReservationReleaseRefVO,
)
from src.modules.inventory.domain.fulfillment_plan.value_object.status import (
    FulfillmentPlanStatus,
)
from src.modules.inventory.domain.stock_reservation.aggregate import StockReservation
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
from src.modules.inventory.domain.value_object.stock_owner_id import StockOwnerIdVO
from src.modules.inventory.domain.value_object.uom_code import UomCodeVO
from src.modules.inventory.domain.warehouse.value_object.identifier import WarehouseIdVO
from src.modules.inventory.domain.inventory_item.value_object.identifier import (
    InventoryItemIdVO,
)


class FulfillmentReservationReleaseDomainTests(unittest.TestCase):
    """Проверяет закрытие, повторы, неизменяемость, хронологию и защиту действующих отгрузок."""

    def setUp(self) -> None:
        """Готовит подтверждённый A=3/B=4 и отдельно закрытый без погашения резерв A."""
        self.f = reservation_fixture.FulfillmentReservationDomainTests()
        self.f.setUp()
        self.plan = self.f.confirm()
        self.at = self.plan.updated_at + timedelta(minutes=2)
        self.closed = self.f.first_reservation.release_all(
            expected_version=self.f.first_reservation.version, updated_at=self.at
        )
        self.snapshot = self.closed.fulfillment_snapshot()
        self.binding = self.f.binding(self.f.f.allocation, self.closed)

    def release(
        self, plan: FulfillmentPlan | None = None, **changes: object
    ) -> FulfillmentPlan:
        """Передаёт ровно выбранное закрытие и текущую версию плана."""
        target = self.plan if plan is None else plan
        return target.release_reservation_confirmations(
            **(
                dict(
                    bindings=(self.binding,),
                    reservations=(self.snapshot,),
                    expected_version=target.version,
                    updated_at=max(target.updated_at, self.at),
                )
                | changes
            )
        )

    def restore(self, plan: FulfillmentPlan, **changes: object) -> FulfillmentPlan:
        """Проверяет полное восстановление истории без текущих внешних объектов."""
        values = {field.name: getattr(plan, field.name) for field in fields(plan)}
        values["identifier"] = values.pop("id")
        return FulfillmentPlan.restore(**(values | changes))

    def replacement(
        self, plan: FulfillmentPlan
    ) -> tuple[FulfillmentPlan, StockReservation]:
        """Заново обеспечивает A новым реальным резервом и сохраняет прежнее подтверждение B."""
        reserve = self.f.reserve(self.f.f.allocation)
        confirmed = self.f.confirm(
            plan,
            bindings=(self.f.binding(self.f.f.allocation, reserve),),
            reservations=(
                reserve.fulfillment_snapshot(),
                self.f.second_reservation.fulfillment_snapshot(),
            ),
            updated_at=self.at,
        )
        return confirmed, reserve

    def test_release_preserves_identity_history_and_other_allocation(self) -> None:
        """Снятие меняет только выбранное подтверждение и одну версию корня."""
        changed = self.release()
        old, new = self.plan.allocations[0], changed.allocations[0]
        self.assertEqual(changed.status, FulfillmentPlanStatus.PARTIALLY_CONFIRMED)
        self.assertEqual(changed.version, self.plan.version + 1)
        self.assertIs(changed.allocations[1], self.plan.allocations[1])
        self.assertIsNone(new.reservation)
        self.assertEqual(new.status, FulfillmentAllocationStatus.PLANNED)
        for name in (
            "id",
            "source_ref",
            "inventory_item_id",
            "base_uom",
            "source",
            "quantity",
        ):
            self.assertEqual(getattr(old, name), getattr(new, name))
        self.assertEqual(
            new.reservation_releases[0],
            FulfillmentReservationReleaseRefVO(
                old.reservation,
                self.closed.version,
                StockReservationStatus.RELEASED,
                self.at,
                self.at,
            ),
        )
        self.assertIsNotNone(old.reservation)
        self.assertEqual(old.reservation_releases, ())
        self.assertEqual(self.closed.status, StockReservationStatus.RELEASED)
        changed.shipment_snapshot().ensure_valid()

    def test_full_batch_is_one_change_and_returns_planned(self) -> None:
        """Оба закрытия снимаются атомарно одной версией без промежуточного состояния."""
        closed_b = self.f.second_reservation.release_all(
            expected_version=1, updated_at=self.at
        )
        changed = self.release(
            bindings=(self.binding, self.f.binding(self.f.second, closed_b)),
            reservations=(self.snapshot, closed_b.fulfillment_snapshot()),
        )
        self.assertEqual(changed.status, FulfillmentPlanStatus.PLANNED)
        self.assertEqual(changed.version, self.plan.version + 1)
        self.assertTrue(all(row.reservation is None for row in changed.allocations))
        self.assertIs(self.restore(changed).status, FulfillmentPlanStatus.PLANNED)

    def test_partial_plan_returns_planned_and_replay_is_same_object(self) -> None:
        """Последнее снятие и его точный повтор не требуют активного подтверждения."""
        changed = self.release(self.f.partial())
        self.assertEqual(changed.status, FulfillmentPlanStatus.PLANNED)
        self.assertIs(
            self.release(changed, updated_at=self.at + timedelta(hours=1)), changed
        )
        self.assertEqual(changed.updated_at, self.at)

    def test_expiry_requires_explicit_transition(self) -> None:
        """Наступивший expires_at не заменяет явный переход StockReservation.expire."""
        reserve = self.f.first_reservation
        at = reserve.expires_at
        with self.assertRaises(InventoryError):
            self.release(
                reservations=(reserve.fulfillment_snapshot(),),
                bindings=(self.f.first_binding,),
                updated_at=at,
            )
        expired = reserve.expire(expected_version=reserve.version, updated_at=at)
        changed = self.release(
            bindings=(self.f.binding(self.f.f.allocation, expired),),
            reservations=(expired.fulfillment_snapshot(),),
            updated_at=at,
        )
        self.assertEqual(
            changed.allocations[0].reservation_releases[0].closed_status,
            StockReservationStatus.EXPIRED,
        )

    def test_reconfirm_uses_new_reserve_and_retains_history(self) -> None:
        """Новый резерв R2 подтверждает ту же Entity с полной сохранностью R1."""
        released = self.release()
        confirmed, reserve = self.replacement(released)
        row = confirmed.allocations[0]
        self.assertEqual(row.reservation.reservation_id, reserve.id)
        self.assertEqual(
            row.reservation_releases, released.allocations[0].reservation_releases
        )
        self.assertEqual(confirmed.status, FulfillmentPlanStatus.CONFIRMED)
        confirmed.shipment_snapshot().ensure_valid()

    def test_old_release_cannot_clear_new_confirmation(self) -> None:
        """Повтор R1 не удаляет действующий R2 даже при новой ожидаемой версии плана."""
        confirmed, _ = self.replacement(self.release())
        with self.assertRaises(InventoryError):
            self.release(confirmed)
        self.assertIsNotNone(confirmed.allocations[0].reservation)

    def test_multiple_cycles_and_old_replay_after_second_release(self) -> None:
        """После снятия R2 можно повторить историческое R1 без добавления записей."""
        confirmed, reserve = self.replacement(self.release())
        closed = reserve.release_all(
            expected_version=reserve.version, updated_at=self.at
        )
        changed = self.release(
            confirmed,
            bindings=(self.f.binding(confirmed.allocations[0], closed),),
            reservations=(closed.fulfillment_snapshot(),),
        )
        self.assertEqual(len(changed.allocations[0].reservation_releases), 2)
        self.assertIs(self.release(changed), changed)
        self.restore(changed)

    def test_historical_id_cannot_be_confirmed_again(self) -> None:
        """Даже подставленный свежий снимок с прежним ID не обходит историю плана."""
        released = self.release()
        fresh = self.f.reserve(self.f.f.allocation, identifier=self.closed.id)
        with self.assertRaises(InventoryError):
            self.f.confirm(
                released,
                bindings=(self.f.binding(released.allocations[0], fresh),),
                reservations=(
                    fresh.fulfillment_snapshot(),
                    self.f.second_reservation.fulfillment_snapshot(),
                ),
                updated_at=self.at,
            )

    def test_mixed_replay_and_new_release_changes_once(self) -> None:
        """Повтор A вместе с новым B не дублирует историю A."""
        released = self.release()
        closed_b = self.f.second_reservation.release_all(
            expected_version=1, updated_at=self.at
        )
        changed = self.release(
            released,
            bindings=(self.binding, self.f.binding(self.f.second, closed_b)),
            reservations=(self.snapshot, closed_b.fulfillment_snapshot()),
        )
        self.assertEqual(changed.version, released.version + 1)
        self.assertEqual(
            changed.allocations[0].reservation_releases,
            released.allocations[0].reservation_releases,
        )
        self.assertEqual(changed.status, FulfillmentPlanStatus.PLANNED)

    def test_invalid_last_entry_leaves_original_batch_unchanged(self) -> None:
        """Неуспешный B не позволяет частично снять A."""
        with self.assertRaises(InventoryError):
            self.release(
                bindings=(self.binding, self.f.second_binding),
                reservations=(
                    self.snapshot,
                    self.f.second_reservation.fulfillment_snapshot(),
                ),
            )
        self.assertTrue(
            all(row.reservation is not None for row in self.plan.allocations)
        )
        self.assertTrue(
            all(not row.reservation_releases for row in self.plan.allocations)
        )

    def test_exact_snapshot_and_binding_sets(self) -> None:
        """Пустые, сырые, повторные и несовпадающие наборы отклоняются."""
        cases = [
            dict(bindings=()),
            dict(bindings=[self.binding]),
            dict(bindings=(object(),)),
            dict(bindings=(self.binding, self.binding)),
            dict(reservations=()),
            dict(reservations=[self.snapshot]),
            dict(reservations=(object(),)),
            dict(reservations=(self.snapshot, self.snapshot)),
            dict(
                reservations=(
                    self.snapshot,
                    self.f.second_reservation.fulfillment_snapshot(),
                )
            ),
            dict(bindings=(replace(self.binding, allocation_id=self.f.second.id),)),
            dict(
                bindings=(
                    replace(self.binding, reservation_id=StockReservationIdVO(uuid4())),
                )
            ),
        ]
        for changes in cases:
            with self.subTest(changes=changes), self.assertRaises(InventoryError):
                self.release(**changes)

    def test_selected_version_must_be_exact_and_newer(self) -> None:
        """Точная выбранная версия закрытия должна превосходить версию подтверждения."""
        for version in (0, 1, 3):
            with self.subTest(version=version), self.assertRaises(InventoryError):
                self.release(
                    bindings=(replace(self.binding, reservation_version=version),)
                )
        stale = replace(self.snapshot, version=1)
        with self.assertRaises(InventoryError):
            self.release(
                bindings=(replace(self.binding, reservation_version=1),),
                reservations=(stale,),
            )

    def test_closed_consumed_quantity_is_not_releasable(self) -> None:
        """Погашение нельзя скрыть даже когда прогресс ещё не зарегистрирован в плане."""
        consumed = self.f.first_reservation.consume(
            QuantityVO(Decimal(1)),
            expected_version=1,
            inventory_item=self.f.f.item,
            consumed_at=self.at,
            updated_at=self.at,
        )
        closed = consumed.release_all(
            expected_version=consumed.version, updated_at=self.at
        )
        with self.assertRaises(InventoryError):
            self.release(
                bindings=(self.f.binding(self.f.f.allocation, closed),),
                reservations=(closed.fulfillment_snapshot(),),
            )

    def test_identity_scope_and_requested_quantity_must_match(self) -> None:
        """Закрытый резерв проверяется по полной товарной и заказной идентичности."""
        variants = [
            replace(self.snapshot, requested_qty=QuantityVO(Decimal(2))),
            replace(
                self.snapshot, source_ref=ReservationSourceVO("order", "other-row")
            ),
            replace(self.snapshot, base_uom=UomCodeVO("KG")),
            replace(
                self.snapshot,
                key=replace(self.snapshot.key, owner_id=StockOwnerIdVO(uuid4())),
            ),
            replace(
                self.snapshot,
                key=replace(self.snapshot.key, warehouse_id=WarehouseIdVO(uuid4())),
            ),
            replace(
                self.snapshot,
                key=replace(
                    self.snapshot.key, inventory_item_id=InventoryItemIdVO(uuid4())
                ),
            ),
        ]
        for snapshot in variants:
            with self.subTest(snapshot=snapshot), self.assertRaises(InventoryError):
                self.release(reservations=(snapshot,))

    def test_changed_history_replay_is_rejected(self) -> None:
        """Повтор обязан предъявить то же закрытие, включая время, статус и версию."""
        released = self.release()
        variants = [
            replace(self.snapshot, version=3),
            replace(self.snapshot, updated_at=self.at + timedelta(seconds=1)),
            replace(self.snapshot, status=StockReservationStatus.EXPIRED),
        ]
        for snapshot in variants:
            with self.subTest(snapshot=snapshot), self.assertRaises(InventoryError):
                self.release(
                    released,
                    reservations=(snapshot,),
                    bindings=(
                        replace(self.binding, reservation_version=snapshot.version),
                    ),
                    updated_at=self.at + timedelta(minutes=1),
                )

    def test_command_versions_and_time_are_validated(self) -> None:
        """Версии без bool, неубывающее время и закрытие не из будущего обязательны."""
        for changes in (
            dict(expected_version=True),
            dict(expected_version=self.plan.version - 1),
            dict(updated_at=self.plan.updated_at - timedelta(seconds=1)),
            dict(updated_at=self.at - timedelta(seconds=1)),
            dict(updated_at=self.at.replace(tzinfo=None)),
        ):
            with self.subTest(changes=changes), self.assertRaises(InventoryError):
                self.release(**changes)
        offset = self.at.astimezone(timezone(timedelta(hours=2)))
        self.assertEqual(self.release(updated_at=offset).updated_at, self.at)

    def test_non_active_plan_statuses_are_rejected(self) -> None:
        """Черновик и отменённый план не допускают снятие подтверждения."""
        cancelled = self.f.plan.cancel(
            expected_version=self.f.plan.version, updated_at=self.at
        )
        for plan in (self.f.f.draft, cancelled):
            with self.subTest(status=plan.status), self.assertRaises(InventoryError):
                self.release(plan)

    def test_assigned_draft_and_confirmed_shipment_block_release(self) -> None:
        """Одного закрытия резерва недостаточно при действующем назначении Shipment."""
        f = assignment_fixture.ShipmentAssignmentDomainTests()
        f.setUp()
        closed = f.f.f.first_reservation.release_all(
            expected_version=1, updated_at=f.at
        )
        with self.assertRaises(InventoryError):
            self.release(
                f.assigned,
                bindings=(f.f.f.binding(f.assigned.allocations[0], closed),),
                reservations=(closed.fulfillment_snapshot(),),
                updated_at=f.at,
            )
        f.confirm()
        with self.assertRaises(InventoryError):
            self.release(
                f.assigned,
                bindings=(f.f.f.binding(f.assigned.allocations[0], closed),),
                reservations=(closed.fulfillment_snapshot(),),
                updated_at=f.at,
            )

    def test_cancel_draft_then_release_assignment_then_confirmation(self) -> None:
        """Отмена черновика открывает штатный путь к снятию резервного подтверждения."""
        f = assignment_fixture.ShipmentAssignmentDomainTests()
        f.setUp()
        unassigned = f.release()
        closed = f.f.f.first_reservation.release_all(
            expected_version=1, updated_at=f.at
        )
        changed = self.release(
            unassigned,
            bindings=(f.f.f.binding(unassigned.allocations[0], closed),),
            reservations=(closed.fulfillment_snapshot(),),
            updated_at=f.at,
        )
        self.assertIsNone(changed.allocations[0].reservation)
        self.assertIsNone(changed.allocations[0].shipment_assignment)
        self.assertEqual(changed.status, FulfillmentPlanStatus.PARTIALLY_CONFIRMED)

    def test_progressed_a_is_preserved_while_b_is_released(self) -> None:
        """Частичное исполнение A сохраняется после снятия ещё не назначенного B."""
        f = progress_fixture.FulfillmentProgressDomainTests()
        f.setUp()
        plan = f.register()
        closed = f.rf.second_reservation.release_all(
            expected_version=1, updated_at=f.at
        )
        changed = self.release(
            plan,
            bindings=(f.rf.binding(f.rf.second, closed),),
            reservations=(closed.fulfillment_snapshot(),),
            updated_at=f.at,
        )
        self.assertIs(changed.allocations[0], plan.allocations[0])
        self.assertEqual(changed.status, FulfillmentPlanStatus.PARTIALLY_FULFILLED)
        changed.shipment_snapshot().ensure_valid()
        closed_a = f.rf.first_reservation.release_all(
            expected_version=1, updated_at=f.at
        )
        with self.assertRaises(InventoryError):
            self.release(
                changed,
                bindings=(f.rf.binding(changed.allocations[0], closed_a),),
                reservations=(closed_a.fulfillment_snapshot(),),
                updated_at=f.at,
            )

    def test_reconfirm_b_preserves_registered_progress_a(self) -> None:
        """Замена резерва B после исполнения A не требует заново подтверждать исторический A."""
        f = progress_fixture.FulfillmentProgressDomainTests()
        f.setUp()
        progressed = f.register()
        closed = f.rf.second_reservation.release_all(
            expected_version=1, updated_at=f.at
        )
        released = self.release(
            progressed,
            bindings=(f.rf.binding(f.rf.second, closed),),
            reservations=(closed.fulfillment_snapshot(),),
            updated_at=f.at,
        )
        reserve = f.rf.reserve(f.rf.second)
        reconfirmed = f.rf.confirm(
            released,
            bindings=(f.rf.binding(f.rf.second, reserve),),
            reservations=(reserve.fulfillment_snapshot(),),
            warehouses=(f.pf.b,),
            updated_at=f.at,
        )
        self.assertIs(reconfirmed.allocations[0], progressed.allocations[0])
        self.assertEqual(reconfirmed.status, FulfillmentPlanStatus.PARTIALLY_FULFILLED)
        self.assertEqual(
            reconfirmed.allocations[1].reservation.reservation_id, reserve.id
        )
        reconfirmed.shipment_snapshot().ensure_valid()

    def test_fulfilled_plan_rejects_release(self) -> None:
        """Завершённый план не открывается повторно через снятие резервов."""
        f = progress_fixture.FulfillmentProgressDomainTests()
        f.setUp()
        a_done = f.execute(f.a, {f.a.lines[0].id: "3"})
        progressed = f.register(shipment=a_done)
        assigned_b, b = f.confirm_b(progressed)
        b_done = f.execute(b, {b.lines[0].id: "4"})
        complete = f.register(assigned_b, b_done)
        self.assertEqual(complete.status, FulfillmentPlanStatus.FULFILLED)
        closed = f.rf.second_reservation.release_all(
            expected_version=1, updated_at=f.at
        )
        with self.assertRaises(InventoryError):
            self.release(
                complete,
                bindings=(f.rf.binding(f.rf.second, closed),),
                reservations=(closed.fulfillment_snapshot(),),
                updated_at=f.at,
            )

    def test_old_draft_cannot_assign_after_reconfirmation(self) -> None:
        """Черновик, построенный по R1, не может получить назначение по R2."""
        f = shipment_fixture.FulfillmentShipmentDomainTests()
        f.setUp()
        draft = f.create()
        closed = f.f.first_reservation.release_all(expected_version=1, updated_at=f.at)
        released = self.release(
            f.plan,
            bindings=(f.f.binding(f.plan.allocations[0], closed),),
            reservations=(closed.fulfillment_snapshot(),),
            updated_at=f.at,
        )
        reserve = f.f.reserve(f.plan.allocations[0])
        confirmed = f.f.confirm(
            released,
            bindings=(f.f.binding(released.allocations[0], reserve),),
            reservations=(
                reserve.fulfillment_snapshot(),
                f.f.second_reservation.fulfillment_snapshot(),
            ),
            updated_at=f.at,
        )
        for plan in (released, confirmed):
            with self.subTest(status=plan.status), self.assertRaises(InventoryError):
                plan.assign_shipment(
                    draft.assignment_snapshot(),
                    expected_version=plan.version,
                    updated_at=f.at,
                )
        new_draft = f.create(
            fulfillment_plan=confirmed.shipment_snapshot(),
            reservations=(reserve.fulfillment_snapshot(),),
        )
        assigned, shipment = f.assign_and_confirm(
            confirmed, new_draft, reservations=(reserve.fulfillment_snapshot(),)
        )
        self.assertIsNotNone(assigned.allocations[0].shipment_assignment)
        self.assertEqual(shipment.lines[0].reservation_id, reserve.id)

    def test_release_vo_is_immutable_normalizes_time_and_rejects_bad_values(
        self,
    ) -> None:
        """VO хранит проверенные факты, не допускает сырые значения и неверную хронологию."""
        ref = self.plan.allocations[0].reservation
        release = FulfillmentReservationReleaseRefVO(
            ref,
            2,
            StockReservationStatus.RELEASED,
            self.at.astimezone(timezone(timedelta(hours=3))),
            self.at,
        )
        self.assertEqual(release.closed_at, self.at)
        with self.assertRaises(FrozenInstanceError):
            release.closed_version = 3
        for changes in (
            dict(confirmation=None),
            dict(closed_version=True),
            dict(closed_version=1),
            dict(closed_status="RELEASED"),
            dict(closed_status=StockReservationStatus.RESERVED),
            dict(closed_at=ref.confirmed_at - timedelta(seconds=1)),
            dict(released_at=self.at - timedelta(seconds=1)),
            dict(closed_at=self.at.replace(tzinfo=None)),
        ):
            with self.subTest(changes=changes), self.assertRaises(InventoryError):
                replace(release, **changes)

    def test_entity_restore_checks_history_shape_and_sequence(self) -> None:
        """Восстановление требует tuple уникальных, хронологических записей."""
        row = self.release().allocations[0]
        record = row.reservation_releases[0]
        for history in (
            [record],
            (object(),),
            (record, record),
            (
                record,
                replace(
                    record,
                    confirmation=FulfillmentReservationRefVO(
                        StockReservationIdVO(uuid4()),
                        1,
                        record.confirmation.confirmed_at,
                    ),
                ),
            ),
        ):
            with self.subTest(history=history), self.assertRaises(InventoryError):
                replace(row, reservation_releases=history).ensure_valid()
        values = {field.name: getattr(row, field.name) for field in fields(row)}
        values["identifier"] = values.pop("id")
        self.assertEqual(FulfillmentAllocation.restore(**values), row)
        for ref in (
            record.confirmation,
            FulfillmentReservationRefVO(
                StockReservationIdVO(uuid4()), 1, self.plan.updated_at
            ),
        ):
            with self.subTest(ref=ref), self.assertRaises(InventoryError):
                replace(
                    row, reservation=ref, status=FulfillmentAllocationStatus.CONFIRMED
                ).ensure_valid()

    def test_root_and_snapshot_check_global_history_and_time(self) -> None:
        """История не может повторять резерв другой строки или выходить за границы корня/снимка."""
        released = self.release()
        row, other = released.allocations
        duplicate = replace(row.reservation_releases[0], confirmation=other.reservation)
        bad_row = replace(row, reservation_releases=(duplicate,))
        with self.assertRaises(InventoryError):
            self.restore(released, allocations=(bad_row, other))
        snapshot = released.shipment_snapshot()
        bad_snapshot_row = replace(
            snapshot.allocations[0], reservation_releases=(duplicate,)
        )
        with self.assertRaises(InventoryError):
            replace(
                snapshot, allocations=(bad_snapshot_row, snapshot.allocations[1])
            ).ensure_valid()
        for changes in (
            dict(updated_at=self.at - timedelta(seconds=1)),
            dict(created_at=self.plan.updated_at + timedelta(seconds=1)),
        ):
            with self.subTest(changes=changes), self.assertRaises(InventoryError):
                self.restore(released, **changes)
        with self.assertRaises(InventoryError):
            replace(snapshot, updated_at=self.at - timedelta(seconds=1)).ensure_valid()

    def test_planned_history_can_be_cancelled_but_not_restored_as_draft(self) -> None:
        """Отмена сохраняет историю; возврат зафиксированного плана в DRAFT запрещён."""
        planned = self.release(self.f.partial())
        cancelled = planned.cancel(expected_version=planned.version, updated_at=self.at)
        self.assertEqual(cancelled.allocations, planned.allocations)
        self.restore(cancelled)
        with self.assertRaises(InventoryError):
            self.restore(planned, status=FulfillmentPlanStatus.DRAFT)

    def test_fractional_quantity_is_preserved_under_small_decimal_context(self) -> None:
        """Снятие не пересчитывает физическое количество и не округляет дробные значения."""
        row = self.plan.allocations[0]
        quantity = QuantityVO(Decimal("123.456789"))
        plan = self.restore(
            self.plan,
            allocations=(replace(row, quantity=quantity, base_uom=UomCodeVO("KG")),),
        )
        snapshot = replace(
            self.snapshot, requested_qty=quantity, base_uom=UomCodeVO("KG")
        )
        with localcontext() as ctx:
            ctx.prec = 2
            ctx.traps[Inexact] = True
            ctx.traps[Rounded] = True
            released = self.release(plan, reservations=(snapshot,))
        self.assertEqual(released.allocations[0].quantity, quantity)


if __name__ == "__main__":
    unittest.main()
