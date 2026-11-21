"""Отгрузки одного склада из подтверждённого плана с обязательной повторной проверкой основания."""

import unittest
from dataclasses import FrozenInstanceError, fields, replace
from datetime import timedelta, timezone
from decimal import Decimal, Inexact, Rounded, localcontext
from uuid import uuid4

from test import test_inventory_fulfillment_reservation_domain as reservation_fixture
from src.modules.inventory.domain.fulfillment_plan.aggregate import FulfillmentPlan
from src.modules.inventory.domain.error import InventoryError, QuantityStepError
from src.modules.inventory.domain.fulfillment_plan.error import (
    FulfillmentPlanStatusError,
    InvalidFulfillmentPlanShipmentSnapshotError,
)
from src.modules.inventory.domain.fulfillment_plan.value_object.allocation_id import (
    FulfillmentAllocationIdVO,
)
from src.modules.inventory.domain.fulfillment_plan.value_object.identifier import (
    FulfillmentPlanIdVO,
)
from src.modules.inventory.domain.fulfillment_plan.value_object.status import (
    FulfillmentPlanStatus,
)
from src.modules.inventory.domain.inventory_item.document_snapshot import (
    InventoryItemDocumentSnapshot,
)
from src.modules.inventory.domain.inventory_item.value_object.identifier import (
    InventoryItemIdVO,
)
from src.modules.inventory.domain.inventory_item.value_object.sku import SkuVO
from src.modules.inventory.domain.inventory_item.value_object.tracking_mode import (
    TrackingMode,
)
from src.modules.inventory.domain.shipment.aggregate import Shipment
from src.modules.inventory.domain.shipment.entity.shipment_line import ShipmentLine
from src.modules.inventory.domain.shipment.registration_snapshot import (
    ShipmentExecutionRegistrationLineSnapshot,
    ShipmentExecutionRegistrationSnapshot,
)
from src.modules.inventory.domain.stock_execution.value_object.identifier import (
    StockExecutionIdVO,
)
from src.modules.inventory.domain.stock_execution.value_object.line_id import (
    StockExecutionLineIdVO,
)
from src.modules.inventory.domain.stock_posting.value_object.operation_type import (
    StockOperationType,
)
from src.modules.inventory.domain.shipment.error import (
    InvalidFulfillmentShipmentLineBindingError,
    InvalidShipmentContextError,
    InvalidShipmentFulfillmentSourceError,
    InvalidShipmentLineError,
    InvalidShipmentValueError,
    ShipmentFulfillmentMismatchError,
    ShipmentFulfillmentSourceRequiredError,
    ShipmentOrderQuantityExceededError,
    ShipmentOrderUnavailableError,
    ShipmentStatusError,
    ShipmentTimeError,
    ShipmentVersionConflictError,
    StaleShipmentFulfillmentSourceError,
)
from src.modules.inventory.domain.shipment.order_snapshot import (
    ShipmentOrderLineSnapshot,
    ShipmentOrderSnapshot,
)
from src.modules.inventory.domain.shipment.value_object.fulfillment_line_binding import (
    FulfillmentShipmentLineBindingVO,
)
from src.modules.inventory.domain.shipment.value_object.fulfillment_source import (
    ShipmentFulfillmentSourceVO,
)
from src.modules.inventory.domain.shipment.value_object.identifier import ShipmentIdVO
from src.modules.inventory.domain.shipment.value_object.line_id import ShipmentLineIdVO
from src.modules.inventory.domain.shipment.value_object.order_ref import (
    ShipmentOrderRefVO,
)
from src.modules.inventory.domain.shipment.value_object.status import ShipmentStatus
from src.modules.inventory.domain.stock_document.aggregate import StockDocument
from src.modules.inventory.domain.stock_document.value_object.identifier import (
    StockDocumentIdVO,
)
from src.modules.inventory.domain.stock_document.value_object.line_id import (
    StockDocumentLineIdVO,
)
from src.modules.inventory.domain.stock_document.value_object.shipment_line_binding import (
    ShipmentDocumentLineBindingVO,
)
from src.modules.inventory.domain.stock_reservation.value_object.source import (
    ReservationSourceVO,
)
from src.modules.inventory.domain.stock_reservation.value_object.status import (
    StockReservationStatus,
)
from src.modules.inventory.domain.value_object.quantity import QuantityVO
from src.modules.inventory.domain.value_object.quantity_conversion_snapshot import (
    QuantityConversionSnapshotVO,
)
from src.modules.inventory.domain.value_object.quantity_rules import QuantityRulesVO
from src.modules.inventory.domain.value_object.stock_owner_id import StockOwnerIdVO
from src.modules.inventory.domain.value_object.uom_code import UomCodeVO
from src.modules.inventory.domain.warehouse.error import WarehouseInactiveError


class FulfillmentShipmentDomainTests(unittest.TestCase):
    """Проверяет основание, полный состав склада, свежие удержания и сохранение прежних сценариев Shipment."""

    def setUp(self) -> None:
        """Готовит подтверждённые 3 PCS с A и 4 PCS с B по реальным фабрикам плана и резервов."""
        self.f = reservation_fixture.FulfillmentReservationDomainTests()
        self.f.setUp()
        self.plan = self.f.confirm()
        self.snapshot = self.plan.shipment_snapshot()
        self.at = self.plan.updated_at + timedelta(minutes=1)
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
                for line in self.f.f.demand.lines
            ),
        )
        self.binding = FulfillmentShipmentLineBindingVO(
            self.f.f.allocation.id, ShipmentLineIdVO(uuid4())
        )
        self.reservation = self.f.first_reservation.fulfillment_snapshot()

    def create(self, **changes: object) -> Shipment:
        """Строит полную отгрузку A по текущим снимкам, позволяя изменять один вход сценария."""
        return Shipment.create_from_fulfillment_plan(
            **(
                dict(
                    identifier=ShipmentIdVO(uuid4()),
                    fulfillment_plan=self.snapshot,
                    warehouse=self.f.f.a,
                    order=self.order,
                    inventory_items=(self.f.f.item,),
                    reservations=(self.reservation,),
                    line_bindings=(self.binding,),
                    created_at=self.at,
                )
                | changes
            )
        )

    def assign_and_confirm(
        self, plan: FulfillmentPlan, shipment: Shipment, **changes: object
    ) -> tuple[FulfillmentPlan, Shipment]:
        """Явно назначает реальный черновик в плане, затем повторно проверяет его перед подтверждением."""
        at = changes.get("updated_at", max(self.at, plan.updated_at))
        assigned = plan.assign_shipment(
            shipment.assignment_snapshot(), expected_version=plan.version, updated_at=at
        )
        confirmed = shipment.confirm_from_fulfillment_plan(
            **(
                dict(
                    expected_version=shipment.version,
                    fulfillment_plan=assigned.shipment_snapshot(),
                    warehouse=self.f.f.a,
                    order=self.order,
                    inventory_items=(self.f.f.item,),
                    reservations=(self.reservation,),
                    updated_at=at,
                )
                | changes
            )
        )
        return assigned, confirmed

    def confirm(self, shipment: Shipment, **changes: object) -> Shipment:
        """Готовит назначение для изолированных проверок Shipment; интеграционные тесты получают оба корня явно."""
        if (
            shipment.status is not ShipmentStatus.DRAFT
            or shipment.fulfillment_source is None
        ):
            return shipment.confirm_from_fulfillment_plan(
                **(
                    dict(
                        expected_version=shipment.version,
                        fulfillment_plan=self.snapshot,
                        warehouse=self.f.f.a,
                        order=self.order,
                        inventory_items=(self.f.f.item,),
                        reservations=(self.reservation,),
                        updated_at=self.at,
                    )
                    | changes
                )
            )
        return self.assign_and_confirm(self.plan, shipment, **changes)[1]

    def restore(self, shipment: Shipment, **changes: object) -> Shipment:
        """Восстанавливает явно весь собственный состав без текущего плана или резервов."""
        values = {
            field.name: getattr(shipment, field.name) for field in fields(shipment)
        }
        values["identifier"] = values.pop("id")
        return Shipment.restore(**(values | changes))

    def test_factory_builds_draft_v0_and_preserves_source_and_allocation(self) -> None:
        """Основание, непрозрачный заказ и полное количество выводятся из плана без его изменения."""
        before = (self.plan, self.f.first_reservation, self.f.second_reservation)
        shipment = self.create()
        self.assertEqual(shipment.status, ShipmentStatus.DRAFT)
        self.assertEqual(shipment.version, 0)
        self.assertEqual(
            shipment.fulfillment_source,
            ShipmentFulfillmentSourceVO(self.plan.id, self.plan.version),
        )
        self.assertEqual(shipment.order_ref, self.order.order_ref)
        self.assertEqual(shipment.order_ref.reference, "000042")
        self.assertEqual(shipment.owner_id, self.plan.owner_id)
        self.assertEqual(shipment.warehouse_id, self.f.f.a.id)
        (line,) = shipment.lines
        self.assertEqual(line.id, self.binding.shipment_line_id)
        self.assertEqual(line.fulfillment_allocation_id, self.binding.allocation_id)
        self.assertEqual(line.reservation_id, self.reservation.id)
        self.assertEqual(line.planned_qty.value, Decimal(3))
        self.assertEqual(line.shipped_qty.value, Decimal(0))
        self.assertEqual(line.conversion.uom, line.base_uom)
        self.assertEqual(line.conversion.factor_to_base, Decimal(1))
        self.assertEqual(
            before, (self.plan, self.f.first_reservation, self.f.second_reservation)
        )
        with self.assertRaises(FrozenInstanceError):
            shipment.version = 99

    def test_warehouses_produce_separate_shipments_and_only_selected_context_is_needed(
        self,
    ) -> None:
        """Один подтверждённый план даёт отдельные 3 и 4 без загрузки резервов другого склада."""
        a = self.create()
        b = self.create(
            warehouse=self.f.f.b,
            reservations=(self.f.second_reservation.fulfillment_snapshot(),),
            line_bindings=(
                FulfillmentShipmentLineBindingVO(
                    self.f.second.id, ShipmentLineIdVO(uuid4())
                ),
            ),
        )
        self.assertEqual(
            [a.lines[0].planned_qty.value, b.lines[0].planned_qty.value],
            [Decimal(3), Decimal(4)],
        )
        self.assertNotEqual(a.warehouse_id, b.warehouse_id)
        self.assertEqual(a.fulfillment_source, b.fulfillment_source)

    def test_snapshot_is_frozen_and_getter_requires_confirmed_allocations(self) -> None:
        """Полное и частичное подтверждение экспортируются; DRAFT/PLANNED/CANCELLED не становятся основанием."""
        self.snapshot.ensure_valid()
        with self.assertRaises(FrozenInstanceError):
            self.snapshot.version = 9
        with self.assertRaises(FrozenInstanceError):
            self.snapshot.allocations[0].quantity = QuantityVO(Decimal(1))
        for plan in (
            self.f.f.draft,
            self.f.plan,
            self.f.f.draft.cancel(expected_version=0, updated_at=self.at),
        ):
            with (
                self.subTest(status=plan.status),
                self.assertRaises(FulfillmentPlanStatusError),
            ):
                plan.shipment_snapshot()
        partial = self.f.partial().shipment_snapshot()
        self.assertEqual(partial.status, FulfillmentPlanStatus.PARTIALLY_CONFIRMED)
        self.assertEqual(
            sum(row.reservation is not None for row in partial.allocations), 1
        )

    def test_snapshot_rejects_raw_headers_and_incomplete_or_duplicate_rows(
        self,
    ) -> None:
        """Поддельный снимок проверяет строгую версию, UTC, непустой tuple и уникальность распределений/резервов."""
        for change in (
            dict(id=uuid4()),
            dict(version=True),
            dict(version=-1),
            dict(version=Decimal(1)),
            dict(status=FulfillmentPlanStatus.PARTIALLY_CONFIRMED),
            dict(status="CONFIRMED"),
            dict(order_ref=self.order.order_ref),
            dict(owner_id=uuid4()),
            dict(updated_at=self.at.replace(tzinfo=None)),
            dict(allocations=[]),
            dict(allocations=()),
            dict(allocations=(object(),)),
            dict(
                allocations=(self.snapshot.allocations[0], self.snapshot.allocations[0])
            ),
        ):
            with self.subTest(change=change), self.assertRaises(InventoryError):
                self.create(fulfillment_plan=replace(self.snapshot, **change))
        row = self.snapshot.allocations[0]
        for change in (
            dict(reservation=None),
            dict(quantity=QuantityVO(Decimal(0))),
            dict(source=object()),
        ):
            with self.subTest(change=change), self.assertRaises(InventoryError):
                replace(row, **change).ensure_valid()
        future = replace(
            row,
            reservation=replace(
                row.reservation, confirmed_at=self.at + timedelta(hours=1)
            ),
        )
        with self.assertRaises(InvalidFulfillmentPlanShipmentSnapshotError):
            replace(self.snapshot, allocations=(future,)).ensure_valid()

    def test_explicit_selection_can_cover_all_or_one_warehouse_allocation(self) -> None:
        """Явный выбор создаёт одну или обе целые Allocation одного склада с ровно выбранными резервами."""
        extra = self.f.f.create_allocation(
            source_ref=self.f.f.other_ref, quantity=QuantityVO(Decimal(2))
        )
        draft = self.f.f.add(self.f.f.one, extra)
        draft = self.f.f.add(draft, self.f.second)
        planned = self.f.f.mark(draft)
        third = self.f.reserve(extra)
        confirmed = self.f.confirm(
            planned,
            bindings=(
                self.f.first_binding,
                self.f.second_binding,
                self.f.binding(extra, third),
            ),
            reservations=(
                self.reservation,
                self.f.second_reservation.fulfillment_snapshot(),
                third.fulfillment_snapshot(),
            ),
        )
        bindings = (
            self.binding,
            FulfillmentShipmentLineBindingVO(extra.id, ShipmentLineIdVO(uuid4())),
        )
        args = dict(
            fulfillment_plan=confirmed.shipment_snapshot(),
            reservations=(third.fulfillment_snapshot(), self.reservation),
            line_bindings=bindings,
        )
        shipment = self.create(**args)
        self.assertEqual(
            {line.planned_qty.value for line in shipment.lines},
            {Decimal(2), Decimal(3)},
        )
        selected = self.create(
            **(
                args
                | dict(line_bindings=(self.binding,), reservations=(self.reservation,))
            )
        )
        self.assertEqual(len(selected.lines), 1)
        self.assertEqual(
            selected.lines[0].fulfillment_allocation_id, self.binding.allocation_id
        )
        self.assertEqual(
            shipment.lines,
            self.create(**(args | dict(line_bindings=bindings[::-1]))).lines,
        )

    def test_binding_ids_types_and_exact_set(self) -> None:
        """Повторы, чужие распределения и raw UUID отклоняются до создания строк."""
        for bindings in (
            None,
            [],
            (),
            (object(),),
            (self.binding, self.binding),
            (replace(self.binding, allocation_id=self.f.second.id),),
            (
                self.binding,
                replace(self.binding, allocation_id=FulfillmentAllocationIdVO(uuid4())),
            ),
        ):
            with (
                self.subTest(bindings=bindings),
                self.assertRaises(InvalidFulfillmentShipmentLineBindingError),
            ):
                self.create(line_bindings=bindings)
        with self.assertRaises(InvalidFulfillmentShipmentLineBindingError):
            FulfillmentShipmentLineBindingVO(uuid4(), self.binding.shipment_line_id)
        with self.assertRaises(InvalidFulfillmentShipmentLineBindingError):
            FulfillmentShipmentLineBindingVO(self.binding.allocation_id, uuid4())

    def test_full_reservation_snapshots_are_required_exactly_once(self) -> None:
        """Старый Shipment-снимок не доказывает запрос/погашение, а лишние резервы другого склада не принимаются."""
        for snapshots in (
            None,
            [],
            (),
            (object(),),
            (self.f.first_reservation.shipment_snapshot(),),
            (self.reservation, self.reservation),
            (self.reservation, self.f.second_reservation.fulfillment_snapshot()),
        ):
            with (
                self.subTest(snapshots=snapshots),
                self.assertRaises(InvalidShipmentContextError),
            ):
                self.create(reservations=snapshots)

    def test_reservation_scope_source_item_owner_and_uom_match_allocation(self) -> None:
        """Полное удержание не подходит другому товару, владельцу, складу, строке или единице."""
        changes = (
            dict(
                key=replace(
                    self.reservation.key, inventory_item_id=InventoryItemIdVO(uuid4())
                )
            ),
            dict(key=replace(self.reservation.key, warehouse_id=self.f.f.b.id)),
            dict(key=replace(self.reservation.key, owner_id=StockOwnerIdVO(uuid4()))),
            dict(source_ref=ReservationSourceVO("order_line", "other")),
            dict(base_uom=UomCodeVO("KG")),
        )
        for change in changes:
            with (
                self.subTest(change=change),
                self.assertRaises(ShipmentFulfillmentMismatchError),
            ):
                self.create(reservations=(replace(self.reservation, **change),))

    def test_only_exact_full_open_unconsumed_reservation_is_accepted(self) -> None:
        """Больший запрос, частичное удержание, ожидание и погашение не подтверждают целую Allocation."""
        cases = (
            dict(
                requested_qty=QuantityVO(Decimal(4)),
                status=StockReservationStatus.PARTIALLY_RESERVED,
            ),
            dict(
                requested_qty=QuantityVO(Decimal(4)),
                reserved_qty=QuantityVO(Decimal(4)),
            ),
            dict(
                reserved_qty=QuantityVO(Decimal(2)),
                status=StockReservationStatus.PARTIALLY_RESERVED,
            ),
            dict(
                reserved_qty=QuantityVO(Decimal(0)),
                status=StockReservationStatus.PENDING,
            ),
            dict(
                reserved_qty=QuantityVO(Decimal(2)),
                consumed_qty=QuantityVO(Decimal(1)),
                status=StockReservationStatus.PARTIALLY_CONSUMED,
            ),
            dict(
                reserved_qty=QuantityVO(Decimal(0)),
                consumed_qty=QuantityVO(Decimal(3)),
                status=StockReservationStatus.CONSUMED,
            ),
            dict(
                reserved_qty=QuantityVO(Decimal(0)),
                status=StockReservationStatus.RELEASED,
            ),
            dict(
                reserved_qty=QuantityVO(Decimal(0)),
                status=StockReservationStatus.EXPIRED,
                expires_at=self.reservation.updated_at,
            ),
        )
        for change in cases:
            snapshot = replace(self.reservation, **change)
            snapshot.ensure_valid()
            with (
                self.subTest(change=change),
                self.assertRaises(ShipmentFulfillmentMismatchError),
            ):
                self.create(reservations=(snapshot,))

    def test_reservation_version_is_exact_even_when_counters_are_unchanged(
        self,
    ) -> None:
        """Прежнее подтверждение не переносится автоматически на новую версию того же удержания."""
        with self.assertRaises(ShipmentFulfillmentMismatchError):
            self.create(
                reservations=(
                    replace(self.reservation, version=self.reservation.version + 1),
                )
            )

    def test_expiration_boundary_and_no_expiration(self) -> None:
        """Ровно на границе удержание непригодно; отсутствие срока допустимо."""
        self.create(reservations=(replace(self.reservation, expires_at=None),))
        with self.assertRaises(ShipmentFulfillmentMismatchError):
            self.create(created_at=self.reservation.expires_at)
        self.create(created_at=self.reservation.expires_at - timedelta(microseconds=1))

    def test_factory_time_is_explicit_utc_and_not_before_plan_or_reservation(
        self,
    ) -> None:
        """Смещение нормализуется, наивное время и будущее состояние отклоняются."""
        offset = self.at.astimezone(timezone(timedelta(hours=3)))
        self.assertEqual(self.create(created_at=offset).created_at, self.at)
        for at in (
            None,
            self.at.replace(tzinfo=None),
            self.plan.updated_at - timedelta(microseconds=1),
        ):
            with self.subTest(at=at), self.assertRaises(ShipmentTimeError):
                self.create(created_at=at)
        with self.assertRaises(ShipmentTimeError):
            self.create(
                reservations=(
                    replace(
                        self.reservation, updated_at=self.at + timedelta(minutes=1)
                    ),
                )
            )

    def test_factory_requires_current_order_membership_availability_and_remaining_quantity(
        self,
    ) -> None:
        """Исторический план не заменяет свежую проверку принадлежности и текущего остатка заказа."""
        for order in (
            replace(self.order, is_fulfillable=False),
            replace(self.order, order_ref=ShipmentOrderRefVO("orders", "42")),
            replace(self.order, lines=()),
            replace(
                self.order,
                lines=(
                    replace(
                        self.order.lines[0],
                        remaining_to_ship_qty=QuantityVO(Decimal(2)),
                    ),
                ),
            ),
        ):
            with self.subTest(order=order), self.assertRaises(InventoryError):
                self.create(order=order)
        with self.assertRaises(ShipmentOrderUnavailableError):
            self.create(order=replace(self.order, is_fulfillable=False))

    def test_current_item_rules_and_active_selected_warehouse_are_checked(self) -> None:
        """Нужен точный набор товаров, текущий шаг и активный склад, выбранный из плана."""
        for items in (None, [], (), (object(),), (self.f.f.item, self.f.f.item)):
            with (
                self.subTest(items=items),
                self.assertRaises(InvalidShipmentContextError),
            ):
                self.create(inventory_items=items)
        with self.assertRaises(QuantityStepError):
            self.create(
                inventory_items=(
                    replace(self.f.f.item, quantity_rules=QuantityRulesVO(Decimal(2))),
                )
            )
        with self.assertRaises(WarehouseInactiveError):
            self.create(warehouse=replace(self.f.f.a, is_active=False))
        with self.assertRaises(InventoryError):
            self.create(warehouse=replace(self.f.f.a, id=self.f.f.b.id))

    def test_confirmation_is_one_transition_and_does_not_update_plan_or_reservations(
        self,
    ) -> None:
        """Повторная проверка переводит DRAFT v0 в CONFIRMED v1 и сохраняет происхождение строк."""
        draft = self.create()
        confirmed = self.confirm(draft)
        self.assertEqual(
            (confirmed.status, confirmed.version), (ShipmentStatus.CONFIRMED, 1)
        )
        self.assertEqual(confirmed.fulfillment_source, draft.fulfillment_source)
        self.assertEqual(confirmed.lines, draft.lines)
        self.assertEqual((draft.status, draft.version), (ShipmentStatus.DRAFT, 0))
        self.assertEqual(self.plan.shipment_snapshot(), self.snapshot)
        self.assertEqual(
            self.f.first_reservation.fulfillment_snapshot(), self.reservation
        )

    def test_confirmation_requires_same_plan_and_no_future_source(self) -> None:
        """Другой план и будущее основание отклоняются; совпадающий состав допускает историческую версию."""
        draft = self.create()
        for change in (
            dict(id=FulfillmentPlanIdVO(uuid4())),
            dict(version=self.snapshot.version - 1),
        ):
            with (
                self.subTest(change=change),
                self.assertRaises(StaleShipmentFulfillmentSourceError),
            ):
                self.confirm(draft, fulfillment_plan=replace(self.snapshot, **change))
        assigned, confirmed = self.assign_and_confirm(self.plan, draft)
        self.assertEqual(confirmed.fulfillment_source, draft.fulfillment_source)
        self.assertEqual(draft.fulfillment_source.plan_version, self.snapshot.version)

    def test_confirmation_rechecks_expiration_release_consumption_and_versions(
        self,
    ) -> None:
        """Изменения после создания черновика обнаруживаются до перехода; исходный черновик не меняется."""
        draft = self.create()
        released = self.f.first_reservation.release_all(
            expected_version=self.f.first_reservation.version, updated_at=self.at
        )
        for snapshot in (
            released.fulfillment_snapshot(),
            replace(self.reservation, version=self.reservation.version + 1),
            replace(
                self.reservation,
                reserved_qty=QuantityVO(Decimal(2)),
                consumed_qty=QuantityVO(Decimal(1)),
                status=StockReservationStatus.PARTIALLY_CONSUMED,
            ),
        ):
            with (
                self.subTest(snapshot=snapshot),
                self.assertRaises(ShipmentFulfillmentMismatchError),
            ):
                self.confirm(draft, reservations=(snapshot,))
        with self.assertRaises(ShipmentFulfillmentMismatchError):
            self.confirm(draft, updated_at=self.reservation.expires_at)
        self.assertEqual(draft.status, ShipmentStatus.DRAFT)

    def test_confirmation_rechecks_current_order_item_and_warehouse(self) -> None:
        """Подтверждение повторяет проверки доступности, шага и остатка, даже если фабрика их уже выполняла."""
        draft = self.create()
        for change, error in (
            (
                dict(order=replace(self.order, is_fulfillable=False)),
                ShipmentOrderUnavailableError,
            ),
            (
                dict(
                    order=replace(
                        self.order,
                        lines=(
                            replace(
                                self.order.lines[0],
                                remaining_to_ship_qty=QuantityVO(Decimal(2)),
                            ),
                        ),
                    )
                ),
                ShipmentOrderQuantityExceededError,
            ),
            (
                dict(
                    inventory_items=(
                        replace(
                            self.f.f.item, quantity_rules=QuantityRulesVO(Decimal(2))
                        ),
                    )
                ),
                QuantityStepError,
            ),
            (
                dict(warehouse=replace(self.f.f.a, is_active=False)),
                WarehouseInactiveError,
            ),
        ):
            with self.subTest(change=change), self.assertRaises(error):
                self.confirm(draft, **change)

    def test_confirmation_rejects_changed_source_fields_and_line_identity(self) -> None:
        """Даже снимок с прежней версией не может скрыто заменить идентичность распределения или владельца."""
        draft = self.create()
        row = next(
            row
            for row in self.snapshot.allocations
            if row.id == self.binding.allocation_id
        )
        for changed in (
            replace(row, quantity=QuantityVO(Decimal(2))),
            replace(row, inventory_item_id=InventoryItemIdVO(uuid4())),
            replace(row, source_ref=ReservationSourceVO("order_line", "changed")),
        ):
            snapshot = replace(
                self.snapshot,
                allocations=tuple(
                    changed if old.id == row.id else old
                    for old in self.snapshot.allocations
                ),
            )
            with (
                self.subTest(row=changed),
                self.assertRaises(InventoryError),
            ):
                self.confirm(draft, fulfillment_plan=snapshot)
        with self.assertRaises(InventoryError):
            self.confirm(
                draft,
                fulfillment_plan=replace(
                    self.snapshot, owner_id=StockOwnerIdVO(uuid4())
                ),
            )
        with self.assertRaises(InventoryError):
            self.confirm(
                self.restore(
                    draft,
                    lines=(
                        replace(
                            draft.lines[0],
                            planned_qty=QuantityVO(Decimal(2)),
                            conversion=QuantityConversionSnapshotVO.create(
                                quantity=QuantityVO(Decimal(2)),
                                uom=UomCodeVO("PCS"),
                                base_uom=UomCodeVO("PCS"),
                            ),
                        ),
                    ),
                )
            )

    def test_manual_confirmation_and_editing_cannot_bypass_source_recheck(self) -> None:
        """Обычный confirm, add/change/remove запрещены для производного черновика, включая численный no-op."""
        draft = self.create()
        args = dict(expected_version=0, updated_at=self.at)
        operations = (
            lambda: draft.confirm(
                **args,
                warehouse=self.f.f.a,
                order=self.order,
                inventory_items=(self.f.f.item,),
                reservations=(self.f.first_reservation.shipment_snapshot(),),
            ),
            lambda: draft.add_line(
                draft.lines[0],
                **args,
                inventory_item=self.f.f.item,
                reservation=self.f.first_reservation.shipment_snapshot(),
            ),
            lambda: draft.change_line_quantity(
                identifier=draft.lines[0].id,
                quantity=draft.lines[0].planned_qty,
                uom=draft.lines[0].base_uom,
                **args,
                inventory_item=self.f.f.item,
                reservation=self.f.first_reservation.shipment_snapshot(),
            ),
            lambda: draft.remove_line(draft.lines[0].id, **args),
        )
        for operation in operations:
            with self.assertRaises(ShipmentFulfillmentSourceRequiredError):
                operation()
        cancelled = draft.cancel(**args)
        self.assertEqual(cancelled.status, ShipmentStatus.CANCELLED)
        self.assertEqual(cancelled.lines, draft.lines)
        self.assertEqual(cancelled.fulfillment_source, draft.fulfillment_source)

    def test_restore_preserves_history_without_current_plan_and_enforces_source_matrix(
        self,
    ) -> None:
        """Историческое восстановление не загружает удержания, но не допускает потерю половины связи."""
        draft = self.create()
        confirmed = self.confirm(draft)
        self.assertEqual(self.restore(confirmed), confirmed)
        for change in (
            dict(fulfillment_source=None),
            dict(lines=()),
            dict(lines=(replace(draft.lines[0], fulfillment_allocation_id=None),)),
        ):
            with self.subTest(change=change), self.assertRaises(InventoryError):
                self.restore(draft, **change)
        with self.assertRaises(InvalidShipmentValueError):
            self.restore(draft, fulfillment_source=object())
        with self.assertRaises(InvalidShipmentLineError):
            replace(draft.lines[0], fulfillment_allocation_id=uuid4()).ensure_valid()

    def test_restore_rejects_duplicate_allocation_and_nonbase_conversion(self) -> None:
        """Собственные инварианты истории запрещают повтор Allocation и иной ввод количества производной строки."""
        draft = self.create()
        line = draft.lines[0]
        duplicate = replace(
            line,
            id=ShipmentLineIdVO(uuid4()),
            reservation_id=self.f.second_reservation.id,
        )
        with self.assertRaises(ShipmentFulfillmentMismatchError):
            self.restore(draft, lines=(line, duplicate))
        weighed = replace(
            line,
            base_uom=UomCodeVO("KG"),
            conversion=QuantityConversionSnapshotVO.create(
                quantity=QuantityVO(Decimal(3000)),
                uom=UomCodeVO("G"),
                base_uom=UomCodeVO("KG"),
            ),
        )
        with self.assertRaises(ShipmentFulfillmentMismatchError):
            self.restore(draft, lines=(weighed,))

    def test_manual_shipment_retains_original_workflow_and_has_no_fulfillment_source(
        self,
    ) -> None:
        """Ручной create/add/confirm остаётся доступен и не получает фиктивное основание."""
        manual = Shipment.create(
            identifier=ShipmentIdVO(uuid4()),
            order_ref=self.order.order_ref,
            warehouse=self.f.f.a,
            owner_id=self.plan.owner_id,
            created_at=self.at,
        )
        line = ShipmentLine.create(
            identifier=ShipmentLineIdVO(uuid4()),
            inventory_item=self.f.f.item,
            reservation=self.f.first_reservation.shipment_snapshot(),
            quantity=QuantityVO(Decimal(2)),
            uom=UomCodeVO("PCS"),
        )
        manual = manual.add_line(
            line,
            expected_version=0,
            inventory_item=self.f.f.item,
            reservation=self.f.first_reservation.shipment_snapshot(),
            updated_at=self.at,
        )
        with self.assertRaises(ShipmentFulfillmentMismatchError):
            self.confirm(manual)
        confirmed = manual.confirm(
            expected_version=1,
            warehouse=self.f.f.a,
            order=self.order,
            inventory_items=(self.f.f.item,),
            reservations=(self.f.first_reservation.shipment_snapshot(),),
            updated_at=self.at,
        )
        self.assertIsNone(confirmed.fulfillment_source)
        self.assertIsNone(confirmed.lines[0].fulfillment_allocation_id)

    def test_source_vo_requires_nominal_id_and_strict_version(self) -> None:
        """Версии bool, отрицательные и числовые альтернативы запрещены; ссылка immutable."""
        for version in (True, False, -1, Decimal(1), "1", None):
            with (
                self.subTest(version=version),
                self.assertRaises(InvalidShipmentFulfillmentSourceError),
            ):
                ShipmentFulfillmentSourceVO(self.plan.id, version)
        with self.assertRaises(InvalidShipmentFulfillmentSourceError):
            ShipmentFulfillmentSourceVO(uuid4(), 1)
        ref = ShipmentFulfillmentSourceVO(self.plan.id, 0)
        with self.assertRaises(FrozenInstanceError):
            ref.plan_version = 2

    def test_confirmation_lifecycle_version_and_time_guards(self) -> None:
        """Доступен только черновик; строгие версии и монотонное явное время обязательны."""
        draft = self.create()
        with self.assertRaises(ShipmentVersionConflictError):
            self.confirm(draft, expected_version=1)
        with self.assertRaises(InvalidShipmentValueError):
            self.confirm(draft, expected_version=True)
        with self.assertRaises(InventoryError):
            self.confirm(draft, updated_at=self.at - timedelta(microseconds=1))
        for shipment in (
            self.confirm(draft),
            draft.cancel(expected_version=0, updated_at=self.at),
        ):
            with self.assertRaises(ShipmentStatusError):
                self.confirm(shipment)

    def test_failure_leaves_all_original_objects_unchanged(self) -> None:
        """Отказ повторной проверки не создаёт прогресс и не переписывает основание ни одного агрегата."""
        draft = self.create()
        before = (draft, self.plan, self.f.first_reservation, self.f.second_reservation)
        with self.assertRaises(ShipmentOrderUnavailableError):
            self.confirm(draft, order=replace(self.order, is_fulfillable=False))
        self.assertEqual(
            before,
            (draft, self.plan, self.f.first_reservation, self.f.second_reservation),
        )
        self.assertEqual(draft.version, 0)

    def test_fractional_quantities_are_exact_under_small_decimal_context(self) -> None:
        """Весовые распределения не округляются при построении и подтверждении Shipment."""
        item = replace(
            self.f.f.item,
            base_uom=UomCodeVO("KG"),
            quantity_rules=QuantityRulesVO(Decimal("0.05")),
        )
        self.f.f.item = item
        first = self.f.f.create_allocation(quantity=QuantityVO(Decimal("3.25")))
        second = self.f.f.create_allocation(
            source=self.f.second.source, quantity=QuantityVO(Decimal("3.75"))
        )
        self.f.f.demand = replace(
            self.f.f.demand,
            lines=tuple(
                replace(row, base_uom=item.base_uom) for row in self.f.f.demand.lines
            ),
        )
        planned = self.f.f.mark(
            self.f.f.add(self.f.f.add(self.f.f.draft, first), second)
        )
        a, b = self.f.reserve(first), self.f.reserve(second)
        plan = self.f.confirm(
            planned,
            bindings=(self.f.binding(first, a), self.f.binding(second, b)),
            reservations=(a.fulfillment_snapshot(), b.fulfillment_snapshot()),
        )
        order = replace(
            self.order,
            lines=tuple(
                replace(row, base_uom=item.base_uom) for row in self.order.lines
            ),
        )
        with localcontext() as context:
            context.prec = 1
            context.traps[Inexact] = True
            context.traps[Rounded] = True
            shipment = self.create(
                fulfillment_plan=plan.shipment_snapshot(),
                order=order,
                reservations=(a.fulfillment_snapshot(),),
                line_bindings=(
                    FulfillmentShipmentLineBindingVO(
                        first.id, self.binding.shipment_line_id
                    ),
                ),
            )
            plan, confirmed = self.assign_and_confirm(
                plan,
                shipment,
                order=order,
                reservations=(a.fulfillment_snapshot(),),
            )
            self.assertEqual(confirmed.lines[0].planned_qty.value, Decimal("3.25"))
            self.assertEqual(confirmed.lines[0].remaining_qty().value, Decimal("3.25"))

    def test_serial_item_keeps_whole_pcs_and_defers_specific_serial_selection(
        self,
    ) -> None:
        """Общий план серийного товара допускает несколько целых PCS без назначения конкретных серий."""
        shipment = self.create(
            inventory_items=(replace(self.f.f.item, tracking_mode=TrackingMode.SERIAL),)
        )
        self.assertEqual(shipment.lines[0].planned_qty.value, Decimal(3))
        self.confirm(
            shipment,
            inventory_items=(
                replace(self.f.f.item, tracking_mode=TrackingMode.SERIAL),
            ),
        )

    def test_consumption_at_other_warehouse_does_not_block_selected_shipment(
        self,
    ) -> None:
        """После погашения A план сохраняет историю, а построение и подтверждение B требуют только ещё открытый B."""
        consumed = self.f.first_reservation.consume(
            self.f.first_reservation.requested_qty,
            expected_version=self.f.first_reservation.version,
            inventory_item=self.f.f.item,
            consumed_at=self.at,
            updated_at=self.at,
        )
        self.assertEqual(consumed.status, StockReservationStatus.CONSUMED)
        self.assertEqual(self.plan.shipment_snapshot(), self.snapshot)
        b = self.f.second_reservation.fulfillment_snapshot()
        shipment = self.create(
            warehouse=self.f.f.b,
            reservations=(b,),
            line_bindings=(
                FulfillmentShipmentLineBindingVO(
                    self.f.second.id, ShipmentLineIdVO(uuid4())
                ),
            ),
        )
        confirmed = self.confirm(shipment, warehouse=self.f.f.b, reservations=(b,))
        self.assertEqual(confirmed.status, ShipmentStatus.CONFIRMED)

    def test_execution_progress_preserves_fulfillment_links_and_history_restore(
        self,
    ) -> None:
        """Частичный и полный прогресс Shipment сохраняют основание и связь Allocation без новых проверок погашенного резерва."""
        shipment = self.confirm(self.create())
        original = shipment.lines[0]
        for quantity in (QuantityVO(Decimal(1)), QuantityVO(Decimal(2))):
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
                        original.id,
                        original.inventory_item_id,
                        original.base_uom,
                        original.reservation_id,
                        quantity,
                        (StockExecutionLineIdVO(uuid4()),),
                    ),
                ),
            )
            shipment = shipment.register_execution(
                registration, expected_version=shipment.version, updated_at=self.at
            )
            self.assertEqual(shipment.fulfillment_source.plan_id, self.plan.id)
            self.assertEqual(
                shipment.lines[0].fulfillment_allocation_id, self.binding.allocation_id
            )
            self.assertEqual(self.restore(shipment), shipment)
        self.assertEqual(shipment.status, ShipmentStatus.SHIPPED)
        self.assertEqual(shipment.lines[0].shipped_qty.value, Decimal(3))

    def test_confirmed_shipment_continues_to_issue_document(self) -> None:
        """Производное отправление работает с прежним построением и подтверждением расходного документа."""
        shipment = self.confirm(self.create())
        item = self.f.f.item
        document_item = InventoryItemDocumentSnapshot(
            item.inventory_item_id,
            SkuVO("OIL-001"),
            item.base_uom,
            item.quantity_rules,
            item.tracking_mode,
        )
        document = StockDocument.create_from_shipment(
            identifier=StockDocumentIdVO(uuid4()),
            shipment=shipment.document_snapshot(),
            warehouse=self.f.f.a,
            inventory_items=(document_item,),
            line_bindings=(
                ShipmentDocumentLineBindingVO(
                    shipment.lines[0].id, StockDocumentLineIdVO(uuid4())
                ),
            ),
            created_at=self.at,
        )
        confirmed = document.confirm(
            shipment=shipment.document_snapshot(),
            warehouse=self.f.f.a,
            inventory_items=(document_item,),
            updated_at=self.at,
        )
        self.assertEqual(confirmed.lines[0].planned_qty.value, Decimal(3))
        self.assertEqual(confirmed.source.reference, str(shipment.id.uuid))


if __name__ == "__main__":
    unittest.main()
