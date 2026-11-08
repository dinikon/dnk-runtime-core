"""Полная отправка подтверждённого заказа и регистрация исполнения в плане."""

import unittest
from dataclasses import replace
from datetime import UTC, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

from src.modules.external_fulfillment.domain.aggregate import SupplierFulfillmentOrder
from src.modules.external_fulfillment.domain.error import (
    InvalidSupplierFulfillmentValueError,
    SupplierFulfillmentBasisMismatchError,
    SupplierFulfillmentStatusError,
    SupplierFulfillmentTimeError,
    SupplierFulfillmentVersionConflictError,
)
from src.modules.external_fulfillment.domain.value_object.identifier import (
    SupplierFulfillmentLineIdVO,
    SupplierFulfillmentShipmentIdVO,
)
from src.modules.external_fulfillment.domain.value_object.quantity import (
    SupplierFulfillmentQuantityVO,
)
from src.modules.external_fulfillment.domain.value_object.shipment import (
    SupplierFulfillmentShipmentLineVO,
    SupplierFulfillmentShipmentVO,
)
from src.modules.external_fulfillment.domain.value_object.status import (
    SupplierFulfillmentOrderStatus,
)
from src.modules.inventory.domain.fulfillment_plan.aggregate import FulfillmentPlan
from src.modules.inventory.domain.fulfillment_plan.error import (
    FulfillmentDemandExceededError,
    FulfillmentPlanTimeError,
    FulfillmentPlanVersionConflictError,
    FulfillmentSupplierOrderShipmentError,
)
from src.modules.inventory.domain.fulfillment_plan.supplier_order_shipment_snapshot import (
    SupplierOrderShipmentSnapshot,
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
from src.modules.inventory.domain.fulfillment_plan.value_object.status import (
    FulfillmentPlanStatus,
)
from src.modules.inventory.domain.fulfillment_plan.value_object.supplier_identity import (
    FulfillmentSupplierIdVO,
    FulfillmentSupplierOrderIdVO,
    FulfillmentSupplierOrderLineIdVO,
    FulfillmentSupplierShipmentIdVO,
)
from src.modules.inventory.domain.fulfillment_plan.value_object.supplier_order_shipment import (
    FulfillmentSupplierOrderShipmentRefVO,
)
from src.modules.inventory.domain.inventory_item.value_object.identifier import (
    InventoryItemIdVO,
)
from src.modules.inventory.domain.value_object.quantity import QuantityVO
from test import test_inventory_fulfillment_progress_domain as progress_fixture
from test import test_supplier_fulfillment_request_domain as request_fixture


class SupplierFulfillmentShipmentDomainTests(unittest.TestCase):
    """Проверяет исполнение без складского резерва и межмодульную сверку факта."""

    def setUp(self) -> None:
        """Готовит смешанный план на 3 PCS склада и 4 PCS поставщика."""
        self.requests = request_fixture.SupplierFulfillmentRequestDomainTests()
        self.requests.setUp()
        self.fixture = self.requests.f.f.f
        self.at = self.requests.at
        self.shipment = SupplierFulfillmentShipmentVO(
            SupplierFulfillmentShipmentIdVO(uuid4()),
            (self.at + timedelta(minutes=1)).astimezone(timezone(timedelta(hours=2))),
            carrier_id="carrier-a",
            tracking_number="TTN-123",
        )
        self.progress = progress_fixture.FulfillmentProgressDomainTests()
        self.progress.setUp()

    @staticmethod
    def shipment_lines(
        order: SupplierFulfillmentOrder,
    ) -> tuple[SupplierFulfillmentShipmentLineVO, ...]:
        """Формирует факт отправки положительно подтверждённых строк."""
        return tuple(
            SupplierFulfillmentShipmentLineVO(line.line_id, line.quantity)
            for line in order.confirmation_snapshot().line_confirmations
            if not line.quantity.value.is_zero()
        )

    def ship(self, order: SupplierFulfillmentOrder) -> SupplierFulfillmentOrder:
        """Регистрирует отправку всего подтверждённого количества."""
        return order.register_shipment(
            self.shipment, self.shipment_lines(order), expected_version=order.version
        )

    def inventory_shipment(
        self, order: SupplierFulfillmentOrder
    ) -> SupplierOrderShipmentSnapshot:
        """Переводит экспорт отправки в специализированный контракт Inventory."""
        snapshot = order.shipment_snapshot()
        return SupplierOrderShipmentSnapshot(
            confirmation=self.requests.map_confirmation(snapshot.confirmation),
            shipment=FulfillmentSupplierOrderShipmentRefVO(
                FulfillmentSupplierShipmentIdVO(snapshot.shipment.id.uuid),
                snapshot.order_version,
                snapshot.shipment.shipped_at,
            ),
            shipped_quantities=tuple(
                (
                    FulfillmentSupplierOrderLineIdVO(line.line_id.uuid),
                    QuantityVO(line.quantity.value),
                )
                for line in snapshot.lines
            ),
        )

    @staticmethod
    def register(
        plan: FulfillmentPlan, snapshot: SupplierOrderShipmentSnapshot
    ) -> FulfillmentPlan:
        """Регистрирует внешний факт в текущей версии плана."""
        return plan.register_supplier_shipment(
            snapshot,
            expected_version=plan.version,
            updated_at=max(plan.updated_at, snapshot.shipment.shipped_at),
        )

    def ship_warehouse(self, plan: FulfillmentPlan) -> FulfillmentPlan:
        """Проводит складскую часть через существующий Shipment."""
        fixture = self.requests.f.f.shipments
        draft = fixture.create(
            fulfillment_plan=plan.shipment_snapshot(), created_at=plan.updated_at
        )
        assigned, confirmed = fixture.assign_and_confirm(plan, draft)
        shipped = self.progress.execute(
            confirmed, {confirmed.lines[0].id: "3"}, at=self.shipment.shipped_at
        )
        return self.progress.register(assigned, shipped)

    def test_full_external_shipment_and_warehouse_in_both_orders(self) -> None:
        """Оба порядка регистрации приводят смешанный план в FULFILLED."""
        requests = self.requests
        assigned = requests.assign(requests.f.f.confirm_warehouse(requests.plan))
        requested = requests.request_order(assigned)
        confirmed = requested.confirm(
            requests.supplier_reply(requested), expected_version=1, confirmed_at=self.at
        )
        plan = requests.register_confirmation(
            assigned, requests.inventory_confirmation(confirmed)
        )
        shipped = self.ship(confirmed)
        self.assertIs(shipped.status, SupplierFulfillmentOrderStatus.SHIPPED)
        self.assertEqual(shipped.version, 3)
        self.assertEqual(shipped.lines[0].shipped_quantity.value, Decimal(4))
        self.assertEqual(shipped.shipment.tracking_number, "TTN-123")
        self.assertEqual(shipped.shipment.carrier_id, "carrier-a")
        self.assertIs(shipped.shipment.shipped_at.tzinfo, UTC)
        self.assertEqual(
            shipped.confirmation_snapshot(), confirmed.confirmation_snapshot()
        )
        self.assertIs(
            shipped.confirm(
                requests.supplier_reply(requested),
                expected_version=3,
                confirmed_at=self.at,
            ),
            shipped,
        )
        self.assertEqual(requests.f.restore(shipped), shipped)
        snapshot = self.inventory_shipment(shipped)
        for external_first in (False, True):
            with self.subTest(external_first=external_first):
                if external_first:
                    intermediate = self.register(plan, snapshot)
                    result = self.ship_warehouse(intermediate)
                else:
                    intermediate = self.ship_warehouse(plan)
                    result = self.register(intermediate, snapshot)
                self.assertIs(
                    intermediate.status, FulfillmentPlanStatus.PARTIALLY_FULFILLED
                )
                self.assertIs(result.status, FulfillmentPlanStatus.FULFILLED)
                self.assertTrue(result.is_fully_confirmed())
                self.assertEqual(
                    result.allocations[0].fulfilled_qty, QuantityVO(Decimal(3))
                )
                supplier = result.get_allocation(requests.f.allocation_id)
                self.assertIs(supplier.status, FulfillmentAllocationStatus.FULFILLED)
                self.assertEqual(supplier.fulfilled_qty, QuantityVO(Decimal(4)))
                self.assertEqual(supplier.supplier_shipment, snapshot.shipment)
                self.assertIsNone(supplier.shipment_progress)
                self.assertIsNone(supplier.reservation)
                self.assertEqual(self.progress.restore(result), result)
                self.assertIs(self.register(result, snapshot), result)
                self.assertIs(
                    requests.register_confirmation(result, snapshot.confirmation),
                    result,
                )

    def test_partial_confirmation_ships_confirmed_quantity_and_can_replan(self) -> None:
        """Отправка 2 из 4 запрошенных закрывает обязательство и оставляет спрос 2 PCS."""
        requests = self.requests
        assigned = requests.assign(requests.f.f.confirm_warehouse(requests.plan))
        requested = requests.request_order(assigned)
        (line,) = requests.supplier_reply(requested)
        confirmed = requested.confirm(
            (replace(line, quantity=SupplierFulfillmentQuantityVO(Decimal(2))),),
            expected_version=1,
            confirmed_at=self.at,
        )
        confirmed_plan = requests.register_confirmation(
            assigned, requests.inventory_confirmation(confirmed)
        )
        shipped = self.ship(confirmed)
        snapshot = self.inventory_shipment(shipped)
        self.assertIs(shipped.status, SupplierFulfillmentOrderStatus.SHIPPED)
        self.assertEqual(shipped.lines[0].requested_quantity.value, Decimal(4))
        self.assertEqual(shipped.lines[0].shipped_quantity.value, Decimal(2))
        result = self.register(self.ship_warehouse(confirmed_plan), snapshot)
        self.assertIs(result.status, FulfillmentPlanStatus.FULFILLED)
        demand = replace(
            self.fixture.demand,
            lines=(
                replace(
                    self.fixture.demand.lines[0], remaining_qty=QuantityVO(Decimal(2))
                ),
                *self.fixture.demand.lines[1:],
            ),
        )
        self.assertEqual(
            result.remaining_to_allocate(self.fixture.line_ref, demand=demand),
            QuantityVO(Decimal(2)),
        )
        original = requests.plan.allocations[0]
        new = replace(
            original,
            id=FulfillmentAllocationIdVO(uuid4()),
            source=replace(original.source, warehouse_id=self.fixture.b.id),
            quantity=QuantityVO(Decimal(2)),
        )
        with self.assertRaises(FulfillmentDemandExceededError):
            result.allocate_remaining_demand(
                allocations=(replace(new, quantity=QuantityVO(Decimal(3))),),
                demand=demand,
                inventory_items=(self.fixture.item,),
                warehouses=(self.fixture.b,),
                expected_version=result.version,
                updated_at=result.updated_at,
            )
        extended = result.allocate_remaining_demand(
            allocations=(new,),
            demand=demand,
            inventory_items=(self.fixture.item,),
            warehouses=(self.fixture.b,),
            expected_version=result.version,
            updated_at=result.updated_at,
        )
        self.assertIs(extended.status, FulfillmentPlanStatus.PARTIALLY_FULFILLED)
        self.assertEqual(extended.allocations[:-1], result.allocations)
        self.assertIs(self.register(extended, snapshot), extended)

    def test_multiline_shipment_is_atomic_and_order_independent(self) -> None:
        """Один факт исполняет всю группу и сохраняет её при восстановлении."""
        requests = self.requests
        plan, draft = requests.two_lines()
        assigned = requests.assign(plan, draft)
        requested = requests.request_order(assigned, draft)
        confirmed = requested.confirm(
            requests.supplier_reply(requested), expected_version=1, confirmed_at=self.at
        )
        registered = requests.register_confirmation(
            assigned, requests.inventory_confirmation(confirmed)
        )
        lines = self.shipment_lines(confirmed)
        shipped = confirmed.register_shipment(
            self.shipment, lines[::-1], expected_version=2
        )
        self.assertIs(
            shipped.register_shipment(self.shipment, lines, expected_version=3), shipped
        )
        self.assertEqual(requests.f.restore(shipped), shipped)
        snapshot = self.inventory_shipment(shipped)
        result = self.register(registered, snapshot)
        self.assertEqual(result.version, registered.version + 1)
        self.assertEqual(result.allocations[0], registered.allocations[0])
        self.assertTrue(
            all(
                row.supplier_shipment == snapshot.shipment
                for row in result.allocations[1:]
            )
        )
        self.assertEqual(self.progress.restore(result), result)
        with self.assertRaises(FulfillmentSupplierOrderShipmentError):
            self.progress.restore(
                result,
                allocations=(*result.allocations[:-1], registered.allocations[-1]),
            )
        with self.assertRaises(InvalidSupplierFulfillmentValueError):
            requests.f.restore(
                shipped, lines=(*shipped.lines[:-1], confirmed.lines[-1])
            )

    def test_zero_confirmation_line_stays_cancelled(self) -> None:
        """Отправка покрывает положительную часть и сохраняет нулевую строку в истории."""
        requests = self.requests
        plan, draft = requests.two_lines()
        assigned = requests.assign(plan, draft)
        requested = requests.request_order(assigned, draft)
        first, second = requests.supplier_reply(requested)
        zero = replace(
            second, quantity=SupplierFulfillmentQuantityVO(Decimal(0)), price=None
        )
        confirmed = requested.confirm(
            (first, zero), expected_version=1, confirmed_at=self.at
        )
        registered = requests.register_confirmation(
            assigned, requests.inventory_confirmation(confirmed)
        )
        shipped = self.ship(confirmed)
        self.assertEqual(shipped.lines[-1].shipped_quantity.value, Decimal(0))
        snapshot = self.inventory_shipment(shipped)
        self.assertEqual(len(snapshot.shipped_quantities), 1)
        result = self.register(registered, snapshot)
        self.assertEqual(result.allocations[-1], registered.allocations[-1])
        self.assertIs(
            result.allocations[-1].status, FulfillmentAllocationStatus.CANCELLED
        )
        self.assertIsNone(result.allocations[-1].supplier_shipment)
        result.shipment_snapshot().ensure_valid()

    def test_external_order_rejects_wrong_status_versions_quantities_and_conflicting_fact(
        self,
    ) -> None:
        """Отправка допускается только после подтверждения и полностью совпадает с ним."""
        requests = self.requests
        assigned = requests.assign()
        requested = requests.request_order(assigned)
        confirmed = requested.confirm(
            requests.supplier_reply(requested), expected_version=1, confirmed_at=self.at
        )
        (line,) = self.shipment_lines(confirmed)
        with self.assertRaises(SupplierFulfillmentStatusError):
            requested.register_shipment(self.shipment, (line,), expected_version=1)
        with self.assertRaises(SupplierFulfillmentStatusError):
            confirmed.shipment_snapshot()
        with self.assertRaises(SupplierFulfillmentVersionConflictError):
            confirmed.register_shipment(self.shipment, (line,), expected_version=1)
        early = replace(self.shipment, shipped_at=self.at - timedelta(seconds=1))
        with self.assertRaises(SupplierFulfillmentTimeError):
            confirmed.register_shipment(early, (line,), expected_version=2)
        for lines in (
            (),
            (line, line),
            (replace(line, line_id=SupplierFulfillmentLineIdVO(uuid4())),),
            (replace(line, quantity=SupplierFulfillmentQuantityVO(Decimal(2))),),
            (replace(line, quantity=SupplierFulfillmentQuantityVO(Decimal(6))),),
        ):
            with (
                self.subTest(lines=lines),
                self.assertRaises(SupplierFulfillmentBasisMismatchError),
            ):
                confirmed.register_shipment(self.shipment, lines, expected_version=2)
        shipped = self.ship(confirmed)
        with self.assertRaises(SupplierFulfillmentBasisMismatchError):
            shipped.register_shipment(
                replace(self.shipment, tracking_number="TTN-456"),
                (line,),
                expected_version=3,
            )
        with self.assertRaises(InvalidSupplierFulfillmentValueError):
            requests.f.restore(shipped, shipment=None)

    def test_inventory_requires_registered_confirmation_and_matching_shipment(
        self,
    ) -> None:
        """План сверяет привязки, количества, версию подтверждения и сам факт."""
        requests = self.requests
        assigned = requests.assign()
        requested = requests.request_order(assigned)
        confirmed = requested.confirm(
            requests.supplier_reply(requested), expected_version=1, confirmed_at=self.at
        )
        snapshot = self.inventory_shipment(self.ship(confirmed))
        with self.assertRaises(FulfillmentSupplierOrderShipmentError):
            self.register(assigned, snapshot)
        plan = requests.register_confirmation(assigned, snapshot.confirmation)
        with self.assertRaises(FulfillmentPlanVersionConflictError):
            plan.register_supplier_shipment(
                snapshot,
                expected_version=plan.version - 1,
                updated_at=self.shipment.shipped_at,
            )
        with self.assertRaises(FulfillmentPlanTimeError):
            plan.register_supplier_shipment(
                snapshot, expected_version=plan.version, updated_at=self.at
            )
        ((line_id, quantity),) = snapshot.shipped_quantities
        confirmation = snapshot.confirmation
        first = confirmation.lines[0]
        for invalid in (
            replace(snapshot, shipped_quantities=((line_id, QuantityVO(Decimal(2))),)),
            replace(
                snapshot, shipped_quantities=((line_id, quantity), (line_id, quantity))
            ),
            replace(
                snapshot,
                confirmation=replace(
                    confirmation, supplier_id=FulfillmentSupplierIdVO(uuid4())
                ),
            ),
            replace(
                snapshot,
                confirmation=replace(
                    confirmation, order_id=FulfillmentSupplierOrderIdVO(uuid4())
                ),
            ),
            replace(
                snapshot,
                confirmation=replace(
                    confirmation, plan_id=FulfillmentPlanIdVO(uuid4())
                ),
            ),
            replace(
                snapshot,
                confirmation=replace(
                    confirmation,
                    confirmation=replace(
                        confirmation.confirmation, confirmed_at=self.shipment.shipped_at
                    ),
                ),
            ),
            replace(
                snapshot,
                confirmation=replace(
                    confirmation,
                    lines=(
                        replace(
                            first,
                            allocation=replace(
                                first.allocation,
                                inventory_item_id=InventoryItemIdVO(uuid4()),
                            ),
                        ),
                    ),
                ),
            ),
        ):
            with (
                self.subTest(snapshot=invalid),
                self.assertRaises(FulfillmentSupplierOrderShipmentError),
            ):
                self.register(plan, invalid)
        result = self.register(plan, snapshot)
        with self.assertRaises(FulfillmentSupplierOrderShipmentError):
            self.register(
                result,
                replace(
                    snapshot,
                    shipment=replace(
                        snapshot.shipment,
                        shipment_id=FulfillmentSupplierShipmentIdVO(uuid4()),
                    ),
                ),
            )

    def test_same_shipment_identity_cannot_execute_two_orders_in_one_plan(self) -> None:
        """Один факт отправки может принадлежать только одному внешнему заказу плана."""
        requests = self.requests
        original, _ = requests.two_lines()
        plan = original
        shipments = []
        for row in original.allocations[1:]:
            basis = requests.f.map_basis(original, row.id)
            draft = requests.f.create(
                basis=basis, line_bindings=requests.f.bindings(basis)
            )
            assigned = requests.assign(plan, draft)
            requested = requests.request_order(assigned, draft)
            confirmed = requested.confirm(
                requests.supplier_reply(requested),
                expected_version=1,
                confirmed_at=self.at,
            )
            plan = requests.register_confirmation(
                assigned, requests.inventory_confirmation(confirmed)
            )
            shipments.append(self.inventory_shipment(self.ship(confirmed)))
        first, second = shipments
        result = self.register(plan, first)
        with self.assertRaises(FulfillmentSupplierOrderShipmentError):
            self.register(result, second)
        self.assertEqual(
            result.allocations[-1].status, FulfillmentAllocationStatus.CONFIRMED
        )
