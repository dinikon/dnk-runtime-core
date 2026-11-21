"""Подтверждение целых распределений текущими резервами без изменения удержаний, пулов или остатков."""

import unittest
from dataclasses import FrozenInstanceError, fields, replace
from datetime import timedelta, timezone
from decimal import Decimal, Inexact, Rounded, localcontext
from uuid import uuid4

from test import test_inventory_fulfillment_plan_domain as plan_fixture
from src.modules.inventory.domain.fulfillment_plan.aggregate import FulfillmentPlan
from src.modules.inventory.domain.availability_pool.reservation_snapshot import (
    AvailabilityPoolReservationSnapshot,
)
from src.modules.inventory.domain.availability_pool.value_object.identifier import (
    AvailabilityPoolIdVO,
)
from src.modules.inventory.domain.availability_pool.value_object.key import (
    AvailabilityPoolKeyVO,
)
from src.modules.inventory.domain.error import InventoryError, QuantityStepError
from src.modules.inventory.domain.fulfillment_plan.entity.fulfillment_allocation import (
    FulfillmentAllocation,
)
from src.modules.inventory.domain.fulfillment_plan.error import (
    FulfillmentDemandExceededError,
    FulfillmentPlanContextError,
    FulfillmentPlanStatusError,
    FulfillmentPlanTimeError,
    FulfillmentPlanVersionConflictError,
    FulfillmentReservationConflictError,
    FulfillmentReservationMismatchError,
    FulfillmentReservationUnavailableError,
    FulfillmentReservationVersionConflictError,
    InvalidFulfillmentPlanValueError,
    InvalidFulfillmentReservationBindingError,
    InvalidFulfillmentReservationRefError,
)
from src.modules.inventory.domain.fulfillment_plan.value_object.allocation_status import (
    FulfillmentAllocationStatus,
)
from src.modules.inventory.domain.fulfillment_plan.value_object.allocation_id import (
    FulfillmentAllocationIdVO,
)
from src.modules.inventory.domain.fulfillment_plan.value_object.reservation_binding import (
    FulfillmentReservationBindingVO,
)
from src.modules.inventory.domain.fulfillment_plan.value_object.reservation_ref import (
    FulfillmentReservationRefVO,
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
from src.modules.inventory.domain.value_object.quantity_rules import QuantityRulesVO
from src.modules.inventory.domain.value_object.stock_owner_id import StockOwnerIdVO
from src.modules.inventory.domain.value_object.uom_code import UomCodeVO
from src.modules.inventory.domain.warehouse.value_object.identifier import WarehouseIdVO


class FulfillmentReservationDomainTests(unittest.TestCase):
    """Проверяет последовательное и пакетное закрепление полных удержаний за собственными складами."""

    def setUp(self) -> None:
        """Готовит PLANNED v3: три PCS с A, четыре с B и два полностью удержанных резерва."""
        self.f = plan_fixture.FulfillmentPlanDomainTests()
        self.f.setUp()
        self.second = self.f.create_allocation(
            source=replace(self.f.source, warehouse_id=self.f.b.id),
            quantity=QuantityVO(Decimal(4)),
        )
        self.plan = self.f.mark(self.f.add(self.f.one, self.second))
        self.at = self.plan.updated_at + timedelta(minutes=1)
        self.first_reservation = self.reserve(self.f.allocation)
        self.second_reservation = self.reserve(self.second)
        self.first_binding = self.binding(self.f.allocation, self.first_reservation)
        self.second_binding = self.binding(self.second, self.second_reservation)

    def reserve(
        self, allocation: FulfillmentAllocation, **changes: object
    ) -> StockReservation:
        """Подготавливает собственный резерв через его фабрику и add_reserved; общий пул этим helper не изменяется."""
        pool = AvailabilityPoolReservationSnapshot(
            AvailabilityPoolIdVO(uuid4()),
            AvailabilityPoolKeyVO(
                allocation.inventory_item_id,
                allocation.source.warehouse_id,
                self.plan.owner_id,
            ),
            allocation.base_uom,
        )
        requested = StockReservation.create(
            **(
                dict(
                    identifier=StockReservationIdVO(uuid4()),
                    pool=pool,
                    inventory_item=self.f.item,
                    source_ref=allocation.source_ref,
                    requested_qty=allocation.quantity,
                    created_at=self.plan.updated_at,
                    expires_at=self.at + timedelta(hours=1),
                )
                | changes
            )
        )
        return requested.add_reserved(
            requested.requested_qty,
            expected_version=requested.version,
            inventory_item=self.f.item,
            updated_at=self.at,
        )

    def binding(
        self, allocation: FulfillmentAllocation, reservation: StockReservation
    ) -> FulfillmentReservationBindingVO:
        """Назначает явно выбранный резерв и текущую версию одной строке плана."""
        return FulfillmentReservationBindingVO(
            allocation.id, reservation.id, reservation.version
        )

    def confirm(
        self, plan: FulfillmentPlan | None = None, **changes: object
    ) -> FulfillmentPlan:
        """Подтверждает по полному текущему контексту плана и заданному набору старых/новых резервов."""
        target = self.plan if plan is None else plan
        return target.confirm_reservations(
            **(
                dict(
                    bindings=(self.first_binding, self.second_binding),
                    reservations=(
                        self.first_reservation.fulfillment_snapshot(),
                        self.second_reservation.fulfillment_snapshot(),
                    ),
                    demand=self.f.demand,
                    inventory_items=(self.f.item,),
                    warehouses=(self.f.a, self.f.b),
                    expected_version=target.version,
                    updated_at=self.at,
                )
                | changes
            )
        )

    def partial(self) -> FulfillmentPlan:
        """Закрепляет только A, оставляя B намерением без ссылки на резерв."""
        return self.confirm(
            bindings=(self.first_binding,),
            reservations=(self.first_reservation.fulfillment_snapshot(),),
        )

    def finish(self, plan: FulfillmentPlan, **changes: object) -> FulfillmentPlan:
        """Передаёт старый A и новый B для повторной проверки перед полным подтверждением."""
        return self.confirm(
            plan,
            **(
                dict(
                    bindings=(self.second_binding,),
                    updated_at=self.at + timedelta(minutes=1),
                )
                | changes
            ),
        )

    def test_batch_confirms_all_allocations_one_plan_version_without_changing_reservations(
        self,
    ) -> None:
        """Два назначения переводят PLANNED v3 в CONFIRMED v4 и сохраняют исходные объекты."""
        before = (self.plan, self.first_reservation, self.second_reservation)
        confirmed = self.confirm()
        self.assertEqual(confirmed.status, FulfillmentPlanStatus.CONFIRMED)
        self.assertEqual(confirmed.version, self.plan.version + 1)
        self.assertEqual(
            before, (self.plan, self.first_reservation, self.second_reservation)
        )
        self.assertEqual(self.plan.status, FulfillmentPlanStatus.PLANNED)
        for allocation, reservation in (
            (self.f.allocation, self.first_reservation),
            (self.second, self.second_reservation),
        ):
            row = confirmed.get_allocation(allocation.id)
            self.assertEqual(row.status, FulfillmentAllocationStatus.CONFIRMED)
            self.assertEqual(
                row.reservation,
                FulfillmentReservationRefVO(
                    reservation.id, reservation.version, self.at
                ),
            )
            self.assertEqual(row.quantity, allocation.quantity)
        self.assertEqual(
            confirmed.remaining_to_allocate(
                self.f.line_ref, demand=self.f.demand
            ).value,
            0,
        )

    def test_sequential_three_plus_four_produces_partial_then_full_confirmation(
        self,
    ) -> None:
        """Подтверждение A сохраняется с первым временем при последующем закреплении B."""
        partial = self.partial()
        self.assertEqual(partial.status, FulfillmentPlanStatus.PARTIALLY_CONFIRMED)
        self.assertEqual(partial.version, 4)
        self.assertEqual(
            partial.get_allocation(self.second.id).status,
            FulfillmentAllocationStatus.PLANNED,
        )
        self.assertIsNone(partial.get_allocation(self.second.id).reservation)
        first_ref = partial.get_allocation(self.f.allocation.id).reservation
        confirmed = self.finish(partial)
        self.assertEqual(confirmed.status, FulfillmentPlanStatus.CONFIRMED)
        self.assertEqual(confirmed.version, 5)
        self.assertEqual(
            confirmed.get_allocation(self.f.allocation.id).reservation, first_ref
        )
        self.assertEqual(
            confirmed.get_allocation(self.second.id).reservation.confirmed_at,
            self.at + timedelta(minutes=1),
        )

    def test_fulfillment_snapshot_contains_request_hold_and_consumption_without_expanding_shipment_contract(
        self,
    ) -> None:
        """Проекция содержит недостающие для проверки величины и сохраняет прежнюю проекцию Shipment."""
        snapshot = self.first_reservation.fulfillment_snapshot()
        snapshot.ensure_valid()
        self.assertEqual(snapshot.requested_qty, self.first_reservation.requested_qty)
        self.assertEqual(snapshot.reserved_qty, self.first_reservation.reserved_qty)
        self.assertEqual(snapshot.consumed_qty.value, 0)
        self.assertEqual(snapshot.pool_id, self.first_reservation.pool_id)
        self.assertEqual(snapshot.version, self.first_reservation.version)
        self.assertFalse(
            hasattr(self.first_reservation.shipment_snapshot(), "requested_qty")
        )
        with self.assertRaises(FrozenInstanceError):
            snapshot.version = 7

    def test_only_planned_or_partially_confirmed_plan_can_confirm(self) -> None:
        """DRAFT, отменённый и уже полностью подтверждённый план не принимают новые назначения."""
        cancelled = self.plan.cancel(
            expected_version=self.plan.version, updated_at=self.at
        )
        for plan in (self.f.draft, cancelled, self.confirm()):
            with (
                self.subTest(status=plan.status),
                self.assertRaises(FulfillmentPlanStatusError),
            ):
                self.confirm(plan)

    def test_bindings_must_be_nonempty_typed_and_unique(self) -> None:
        """Пустой набор, повтор распределения/резерва, отсутствующее распределение и сырые назначения запрещены."""
        for bindings in (
            (),
            [self.first_binding],
            (None,),
            (self.first_binding, self.first_binding),
            (
                self.first_binding,
                replace(
                    self.second_binding,
                    reservation_id=self.first_binding.reservation_id,
                ),
            ),
            (
                replace(
                    self.first_binding, allocation_id=FulfillmentAllocationIdVO(uuid4())
                ),
            ),
        ):
            with self.subTest(bindings=bindings), self.assertRaises(InventoryError):
                self.confirm(bindings=bindings)

    def test_reservation_context_is_exact_union_of_old_and_new(self) -> None:
        """Первый пакет не требует неназначенный B, последующий обязан включать ранее закреплённый A."""
        first, second = (
            self.first_reservation.fulfillment_snapshot(),
            self.second_reservation.fulfillment_snapshot(),
        )
        for reservations in (
            (),
            (first,),
            (first, first),
            [first, second],
            (first, second, replace(second, id=StockReservationIdVO(uuid4()))),
            (self.first_reservation.shipment_snapshot(), second),
        ):
            with (
                self.subTest(reservations=reservations),
                self.assertRaises(InventoryError),
            ):
                self.confirm(reservations=reservations)
        partial = self.partial()
        with self.assertRaises(FulfillmentPlanContextError):
            self.finish(partial, reservations=(second,))
        with self.assertRaises(FulfillmentPlanContextError):
            self.confirm(bindings=(self.first_binding,), reservations=(first, second))

    def test_requested_amount_and_full_hold_must_equal_allocation(self) -> None:
        """Полный резерв на пять не подтверждает распределение на три; частичный резерв тоже не подходит."""
        too_large = self.reserve(
            self.f.allocation, requested_qty=QuantityVO(Decimal(5))
        )
        with self.assertRaises(FulfillmentReservationMismatchError):
            self.confirm(
                bindings=(self.binding(self.f.allocation, too_large),),
                reservations=(too_large.fulfillment_snapshot(),),
            )
        partial = self.first_reservation.release(
            QuantityVO(Decimal(1)),
            expected_version=self.first_reservation.version,
            inventory_item=self.f.item,
            updated_at=self.at,
        )
        with self.assertRaises(FulfillmentReservationUnavailableError):
            self.confirm(
                bindings=(self.binding(self.f.allocation, partial),),
                reservations=(partial.fulfillment_snapshot(),),
            )

    def test_pending_consumed_released_and_expired_reservations_are_not_confirmation(
        self,
    ) -> None:
        """Ожидание, расход, освобождение и явное истечение не подменяют полное открытое удержание."""
        original = self.first_reservation
        values = {
            field.name: getattr(original, field.name) for field in fields(original)
        }
        values["identifier"] = values.pop("id")
        variants = (
            dict(
                status=StockReservationStatus.PENDING,
                reserved_qty=QuantityVO(Decimal(0)),
            ),
            dict(
                status=StockReservationStatus.CONSUMED,
                reserved_qty=QuantityVO(Decimal(0)),
                consumed_qty=original.requested_qty,
            ),
            dict(
                status=StockReservationStatus.RELEASED,
                reserved_qty=QuantityVO(Decimal(0)),
            ),
            dict(
                status=StockReservationStatus.EXPIRED,
                reserved_qty=QuantityVO(Decimal(0)),
                updated_at=original.expires_at,
            ),
        )
        for changes in variants:
            reservation = StockReservation.restore(**(values | changes))
            snapshot = reservation.fulfillment_snapshot()
            snapshot.ensure_valid()
            with (
                self.subTest(status=reservation.status),
                self.assertRaises(FulfillmentReservationUnavailableError),
            ):
                self.confirm(
                    bindings=(self.binding(self.f.allocation, reservation),),
                    reservations=(snapshot,),
                    updated_at=reservation.updated_at,
                )

    def test_partially_consumed_reservation_is_not_reused_for_full_confirmation(
        self,
    ) -> None:
        """Даже ненулевое оставшееся удержание с уже погашенным количеством не подходит первому подтверждению."""
        consumed = self.first_reservation.consume(
            QuantityVO(Decimal(1)),
            expected_version=self.first_reservation.version,
            inventory_item=self.f.item,
            consumed_at=self.at,
            updated_at=self.at,
        )
        with self.assertRaises(FulfillmentReservationUnavailableError):
            self.confirm(
                bindings=(self.binding(self.f.allocation, consumed),),
                reservations=(consumed.fulfillment_snapshot(),),
            )

    def test_source_item_owner_warehouse_and_unit_must_match(self) -> None:
        """Одинакового количества недостаточно для резерва другой строки обязательства или области."""
        snapshot = self.first_reservation.fulfillment_snapshot()
        variants = (
            replace(snapshot, source_ref=ReservationSourceVO("order_line", "foreign")),
            replace(
                snapshot,
                key=replace(
                    snapshot.key,
                    inventory_item_id=self.f.item.inventory_item_id.__class__(uuid4()),
                ),
            ),
            replace(
                snapshot, key=replace(snapshot.key, owner_id=StockOwnerIdVO(uuid4()))
            ),
            replace(snapshot, key=replace(snapshot.key, warehouse_id=self.f.b.id)),
            replace(snapshot, base_uom=UomCodeVO("KG")),
        )
        for current in variants:
            with (
                self.subTest(current=current),
                self.assertRaises(FulfillmentReservationMismatchError),
            ):
                self.confirm(bindings=(self.first_binding,), reservations=(current,))

    def test_new_binding_requires_exact_selected_reservation_version(self) -> None:
        """Версия назначения сравнивается со свежим снимком, даже если количество одинаково."""
        with self.assertRaises(FulfillmentReservationVersionConflictError):
            self.confirm(
                bindings=(
                    replace(
                        self.first_binding,
                        reservation_version=self.first_binding.reservation_version + 1,
                    ),
                ),
                reservations=(self.first_reservation.fulfillment_snapshot(),),
            )

    def test_existing_reservation_version_is_rechecked_without_silent_rebinding(
        self,
    ) -> None:
        """Новая версия старого A блокирует закрепление B, сохраняя прежнюю ссылку и состояние плана."""
        partial = self.partial()
        changed = replace(
            self.first_reservation.fulfillment_snapshot(),
            version=self.first_reservation.version + 1,
        )
        with self.assertRaises(FulfillmentReservationVersionConflictError):
            self.finish(
                partial,
                reservations=(changed, self.second_reservation.fulfillment_snapshot()),
            )
        self.assertEqual(partial.status, FulfillmentPlanStatus.PARTIALLY_CONFIRMED)
        self.assertIsNone(partial.get_allocation(self.second.id).reservation)

    def test_existing_hold_is_revalidated_before_last_confirmation(self) -> None:
        """Истёкший, освобождённый или погашенный старый резерв не позволяет объявить весь план подтверждённым."""
        partial = self.partial()
        original = self.first_reservation.fulfillment_snapshot()
        for current in (
            replace(
                original,
                status=StockReservationStatus.RELEASED,
                reserved_qty=QuantityVO(Decimal(0)),
            ),
            replace(
                original,
                status=StockReservationStatus.PARTIALLY_CONSUMED,
                reserved_qty=QuantityVO(Decimal(2)),
                consumed_qty=QuantityVO(Decimal(1)),
            ),
        ):
            with (
                self.subTest(current=current),
                self.assertRaises(FulfillmentReservationUnavailableError),
            ):
                self.finish(
                    partial,
                    reservations=(
                        current,
                        self.second_reservation.fulfillment_snapshot(),
                    ),
                )
        with self.assertRaises(FulfillmentReservationUnavailableError):
            self.finish(partial, updated_at=self.first_reservation.expires_at)

    def test_expiration_boundary_is_exclusive_and_missing_deadline_is_allowed(
        self,
    ) -> None:
        """В момент expires_at подтверждение запрещено; отсутствие срока не запрещает полное удержание."""
        with self.assertRaises(FulfillmentReservationUnavailableError):
            self.confirm(updated_at=self.first_reservation.expires_at)
        no_expiry = replace(
            self.first_reservation.fulfillment_snapshot(), expires_at=None
        )
        partial = self.confirm(
            bindings=(self.first_binding,), reservations=(no_expiry,)
        )
        self.assertEqual(partial.status, FulfillmentPlanStatus.PARTIALLY_CONFIRMED)

    def test_confirmation_is_not_earlier_than_any_current_reservation_snapshot(
        self,
    ) -> None:
        """Явное время подтверждения должно быть не раньше версии всех входных резервов."""
        late = replace(
            self.first_reservation.fulfillment_snapshot(),
            updated_at=self.at + timedelta(minutes=1),
        )
        with self.assertRaises(FulfillmentPlanTimeError):
            self.confirm(bindings=(self.first_binding,), reservations=(late,))

    def test_current_demand_is_checked_for_the_entire_plan_again(self) -> None:
        """Изменение потребности или разрешения разделения блокирует подтверждение при подходящих резервах."""
        reduced = replace(
            self.f.demand,
            lines=(
                replace(self.f.first_demand, remaining_qty=QuantityVO(Decimal(6))),
                self.f.other_demand,
            ),
        )
        with self.assertRaises(FulfillmentDemandExceededError):
            self.confirm(demand=reduced)
        for demand in (
            replace(self.f.demand, is_fulfillable=False),
            replace(
                self.f.demand,
                lines=(replace(self.f.first_demand, allow_source_split=False),),
            ),
        ):
            with self.assertRaises(InventoryError):
                self.confirm(demand=demand)

    def test_all_plan_items_and_warehouses_must_still_be_compatible(self) -> None:
        """Проверяются правила всего плана, включая ещё не подтверждаемый склад и уже закреплённый товар."""
        with self.assertRaises(QuantityStepError):
            self.confirm(
                inventory_items=(
                    replace(self.f.item, quantity_rules=QuantityRulesVO(Decimal(2))),
                )
            )
        with self.assertRaises(InventoryError):
            self.confirm(
                bindings=(self.first_binding,),
                reservations=(self.first_reservation.fulfillment_snapshot(),),
                warehouses=(self.f.a, replace(self.f.b, is_active=False)),
            )
        for changes in (
            dict(inventory_items=()),
            dict(warehouses=(self.f.a,)),
            dict(inventory_items=[self.f.item]),
        ):
            with self.subTest(changes=changes), self.assertRaises(InventoryError):
                self.confirm(**changes)

    def test_repeated_confirmation_or_reservation_reuse_is_rejected(self) -> None:
        """Существующую привязку нельзя перезаписать повтором или назначением её резерва другой строке."""
        partial = self.partial()
        with self.assertRaises(FulfillmentReservationConflictError):
            self.confirm(partial, bindings=(self.first_binding,))
        with self.assertRaises(FulfillmentReservationConflictError):
            self.finish(
                partial,
                bindings=(
                    replace(
                        self.second_binding, reservation_id=self.first_reservation.id
                    ),
                ),
            )
        with self.assertRaises(FulfillmentReservationConflictError):
            partial.get_allocation(self.f.allocation.id).confirm_reservation(
                FulfillmentReservationRefVO(StockReservationIdVO(uuid4()), 1, self.at)
            )

    def test_partial_and_confirmed_plans_cannot_be_cancelled_or_manually_edited(
        self,
    ) -> None:
        """Наличие подтверждений требует отдельного сценария освобождения обязательств."""
        for plan in (self.partial(), self.confirm()):
            with self.subTest(status=plan.status):
                with self.assertRaises(FulfillmentPlanStatusError):
                    plan.cancel(
                        expected_version=plan.version, updated_at=plan.updated_at
                    )
                with self.assertRaises(FulfillmentPlanStatusError):
                    plan.remove_allocation(
                        self.f.allocation.id,
                        expected_version=plan.version,
                        updated_at=plan.updated_at,
                    )
                with self.assertRaises(FulfillmentPlanStatusError):
                    self.f.mark(plan)

    def test_restore_preserves_history_without_loading_current_holds(self) -> None:
        """Исторические статус/ссылка/момент восстанавливаются, не переоценивая истечение резерва."""
        partial = self.partial()
        confirmed = self.finish(partial)
        self.assertEqual(self.f.restore(partial), partial)
        self.assertEqual(
            self.f.restore(
                confirmed, updated_at=confirmed.updated_at + timedelta(days=10)
            ).allocations,
            confirmed.allocations,
        )
        self.assertEqual(
            confirmed.get_allocation(self.f.allocation.id).reservation.confirmed_at,
            self.at,
        )

    def test_restore_checks_parent_status_matrix_and_unique_reservations(self) -> None:
        """Собственный состав не допускает подтверждённые строки в DRAFT/PLANNED/CANCELLED либо ложный полный статус."""
        partial = self.partial()
        confirmed = self.confirm()
        for status in (
            FulfillmentPlanStatus.DRAFT,
            FulfillmentPlanStatus.PLANNED,
            FulfillmentPlanStatus.CANCELLED,
            FulfillmentPlanStatus.CONFIRMED,
        ):
            with (
                self.subTest(status=status),
                self.assertRaises(InvalidFulfillmentPlanValueError),
            ):
                self.f.restore(partial, status=status)
        with self.assertRaises(InvalidFulfillmentPlanValueError):
            self.f.restore(confirmed, status=FulfillmentPlanStatus.PARTIALLY_CONFIRMED)
        duplicate = replace(
            confirmed.allocations[1], reservation=confirmed.allocations[0].reservation
        )
        with self.assertRaises(FulfillmentReservationConflictError):
            self.f.restore(confirmed, allocations=(confirmed.allocations[0], duplicate))

    def test_restore_checks_confirmation_timestamps_and_child_status_matrix(
        self,
    ) -> None:
        """Моменты подтверждений принадлежат истории корня; ссылка обязательна только подтверждённой Entity."""
        partial = self.partial()
        row = partial.get_allocation(self.f.allocation.id)
        for moment in (
            self.plan.created_at - timedelta(seconds=1),
            partial.updated_at + timedelta(seconds=1),
        ):
            with (
                self.subTest(moment=moment),
                self.assertRaises(FulfillmentPlanTimeError),
            ):
                self.f.restore(
                    partial,
                    allocations=(
                        replace(
                            row,
                            reservation=replace(row.reservation, confirmed_at=moment),
                        ),
                        self.second,
                    ),
                )
        for child in (
            replace(row, status=FulfillmentAllocationStatus.PLANNED),
            replace(row, reservation=None),
            replace(self.second, reservation=row.reservation),
        ):
            with self.subTest(child=child), self.assertRaises(InventoryError):
                child.ensure_valid()

    def test_confirmed_child_cannot_be_added_to_a_draft_as_a_bypass(self) -> None:
        """Подтверждение проходит через корень, а не ручную вставку заранее связанной Entity."""
        row = self.partial().get_allocation(self.f.allocation.id)
        with self.assertRaises(InvalidFulfillmentPlanValueError):
            self.f.add(self.f.draft, row)

    def test_binding_and_reference_values_validate_nominal_ids_versions_and_utc(
        self,
    ) -> None:
        """VO проверяют собственные типы без загрузки резерва; ссылка нормализует время."""
        ref = FulfillmentReservationRefVO(
            self.first_reservation.id,
            1,
            self.at.astimezone(timezone(timedelta(hours=3))),
        )
        self.assertEqual(ref.confirmed_at, self.at)
        for version in (True, -1, Decimal(1)):
            with self.subTest(version=version):
                with self.assertRaises(InvalidFulfillmentReservationBindingError):
                    replace(self.first_binding, reservation_version=version)
                with self.assertRaises(InvalidFulfillmentReservationRefError):
                    replace(ref, version=version)
        with self.assertRaises(InvalidFulfillmentReservationBindingError):
            replace(self.first_binding, allocation_id=self.first_reservation.id)
        with self.assertRaises(InventoryError):
            replace(ref, confirmed_at=self.at.replace(tzinfo=None))

    def test_plan_expected_version_and_time_are_checked_before_confirmation(
        self,
    ) -> None:
        """Повтор по старой версии, bool и убывающее время не создают новых ссылок."""
        with self.assertRaises(FulfillmentPlanVersionConflictError):
            self.confirm(expected_version=self.plan.version - 1)
        with self.assertRaises(InvalidFulfillmentPlanValueError):
            self.confirm(expected_version=True)
        with self.assertRaises(FulfillmentPlanTimeError):
            self.confirm(updated_at=self.plan.updated_at - timedelta(seconds=1))
        with self.assertRaises(FulfillmentPlanTimeError):
            self.confirm(updated_at=self.at.replace(tzinfo=None))

    def test_snapshot_accounting_rejects_raw_or_inconsistent_counter_states(
        self,
    ) -> None:
        """Публичный снимок не доверяет одному тегу RESERVED и проверяет собственные счётчики."""
        snapshot = self.first_reservation.fulfillment_snapshot()
        for changes in (
            dict(requested_qty=Decimal(3)),
            dict(consumed_qty=Decimal(0)),
            dict(version=True),
            dict(requested_qty=QuantityVO(Decimal(2))),
            dict(requested_qty=QuantityVO(Decimal(5))),
            dict(consumed_qty=QuantityVO(Decimal(1))),
            dict(status=StockReservationStatus.PENDING),
            dict(updated_at=self.at.replace(tzinfo=None)),
        ):
            with self.subTest(changes=changes), self.assertRaises(InventoryError):
                replace(snapshot, **changes).ensure_valid()

    def test_equal_numeric_request_and_hold_do_not_round_under_small_decimal_context(
        self,
    ) -> None:
        """Полное обеспечение проверяется точно и не зависит от глобальной точности Decimal."""
        with localcontext() as context:
            context.prec = 1
            context.traps[Inexact] = context.traps[Rounded] = True
            confirmed = self.confirm()
            self.assertEqual(confirmed.status, FulfillmentPlanStatus.CONFIRMED)

    def test_fractional_weight_reservations_are_compared_exactly(self) -> None:
        """Распределения 3.25 и 4.25 KG подтверждаются без округления при глобальной точности 1."""
        self.f.item = replace(
            self.f.item,
            base_uom=UomCodeVO("KG"),
            quantity_rules=QuantityRulesVO(Decimal("0.05")),
        )
        self.f.first_demand = replace(
            self.f.first_demand,
            base_uom=self.f.item.base_uom,
            remaining_qty=QuantityVO(Decimal("7.50")),
        )
        self.f.demand = replace(self.f.demand, lines=(self.f.first_demand,))
        self.f.allocation = self.f.create_allocation(
            quantity=QuantityVO(Decimal("3.25"))
        )
        self.second = self.f.create_allocation(
            source=replace(self.f.source, warehouse_id=self.f.b.id),
            quantity=QuantityVO(Decimal("4.25")),
        )
        first = self.f.add(self.f.draft, self.f.allocation)
        self.plan = self.f.mark(self.f.add(first, self.second))
        self.first_reservation, self.second_reservation = self.reserve(
            self.f.allocation
        ), self.reserve(self.second)
        self.first_binding, self.second_binding = self.binding(
            self.f.allocation, self.first_reservation
        ), self.binding(self.second, self.second_reservation)
        with localcontext() as context:
            context.prec = 1
            context.traps[Inexact] = context.traps[Rounded] = True
            self.assertEqual(self.confirm().status, FulfillmentPlanStatus.CONFIRMED)

    def test_failed_last_confirmation_does_not_mutate_any_candidate(self) -> None:
        """Отказ по последнему B сохраняет прежние ссылки и не изменяет переданные резервы."""
        partial = self.partial()
        before = (partial, self.first_reservation, self.second_reservation)
        wrong = replace(
            self.second_reservation.fulfillment_snapshot(),
            key=replace(self.second_reservation.key, owner_id=StockOwnerIdVO(uuid4())),
        )
        with self.assertRaises(FulfillmentReservationMismatchError):
            self.finish(
                partial,
                reservations=(self.first_reservation.fulfillment_snapshot(), wrong),
            )
        self.assertEqual(
            before, (partial, self.first_reservation, self.second_reservation)
        )
        self.assertIsNone(partial.get_allocation(self.second.id).reservation)


if __name__ == "__main__":
    unittest.main()
