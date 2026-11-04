"""Первый план собственной отгрузки: строки заказа, текущие удержания и подтверждение без расхода."""

import unittest
from dataclasses import FrozenInstanceError, replace
from datetime import UTC, datetime, timedelta, timezone
from decimal import Decimal, Inexact, Rounded, localcontext
from unittest.mock import patch
from uuid import uuid4

from src.modules.inventory.domain.availability_pool.aggregate import AvailabilityPool
from src.modules.inventory.domain.availability_pool.value_object.identifier import (
    AvailabilityPoolIdVO,
)
from src.modules.inventory.domain.availability_pool.value_object.key import (
    AvailabilityPoolKeyVO,
)
from src.modules.inventory.domain.error import (
    IncompatibleUomError,
    InventoryError,
    QuantityConversionMismatchError,
    QuantityStepError,
    StockQuantityArithmeticError,
    UnknownUomError,
)
from src.modules.inventory.domain.inventory_item.aggregate import InventoryItem
from src.modules.inventory.domain.inventory_item.error import (
    InvalidInventoryItemStockSnapshotError,
)
from src.modules.inventory.domain.inventory_item.value_object.identifier import (
    InventoryItemIdVO,
)
from src.modules.inventory.domain.inventory_item.value_object.sku import SkuVO
from src.modules.inventory.domain.inventory_item.value_object.tracking_mode import (
    TrackingMode,
)
from src.modules.inventory.domain.policy.shipment_confirmation import (
    ShipmentConfirmationPolicy,
)
from src.modules.inventory.domain.shipment.aggregate import Shipment
from src.modules.inventory.domain.shipment.entity.shipment_line import ShipmentLine
from src.modules.inventory.domain.shipment.error import (
    EmptyShipmentError,
    InvalidShipmentContextError,
    InvalidShipmentLineError,
    InvalidShipmentOrderRefError,
    InvalidShipmentOrderSnapshotError,
    InvalidShipmentValueError,
    ShipmentItemMismatchError,
    ShipmentLineConflictError,
    ShipmentLineNotFoundError,
    ShipmentOrderQuantityExceededError,
    ShipmentOrderUnavailableError,
    ShipmentReservationMismatchError,
    ShipmentReservationQuantityExceededError,
    ShipmentReservationUnavailableError,
    ShipmentStatusError,
    ShipmentTimeError,
    ShipmentUomMismatchError,
    ShipmentVersionConflictError,
)
from src.modules.inventory.domain.shipment.order_snapshot import (
    ShipmentOrderLineSnapshot,
    ShipmentOrderSnapshot,
)
from src.modules.inventory.domain.shipment.value_object.identifier import ShipmentIdVO
from src.modules.inventory.domain.shipment.value_object.line_id import ShipmentLineIdVO
from src.modules.inventory.domain.shipment.value_object.order_ref import (
    ShipmentOrderRefVO,
)
from src.modules.inventory.domain.shipment.value_object.status import ShipmentStatus
from src.modules.inventory.domain.stock_reservation.aggregate import StockReservation
from src.modules.inventory.domain.stock_reservation.error import (
    InvalidStockReservationShipmentSnapshotError,
    InvalidStockReservationValueError,
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
from src.modules.inventory.domain.value_object.quantity_conversion_snapshot import (
    QuantityConversionSnapshotVO,
)
from src.modules.inventory.domain.value_object.quantity_rules import QuantityRulesVO
from src.modules.inventory.domain.value_object.stock_owner_id import StockOwnerIdVO
from src.modules.inventory.domain.value_object.uom_code import UomCodeVO
from src.modules.inventory.domain.warehouse.error import (
    InvalidWarehouseSnapshotError,
    WarehouseInactiveError,
)
from src.modules.inventory.domain.warehouse.snapshot import WarehouseSnapshot
from src.modules.inventory.domain.warehouse.value_object.identifier import WarehouseIdVO


class ShipmentDomainTests(unittest.TestCase):
    """Проверяет границы плана и ограничения заказа/удержаний без прикладной оркестрации."""

    def setUp(self) -> None:
        """Готовит заказ на 7 KG, два удержания 4+3 KG и план 3+2 KG одной строки заказа."""
        self.time = datetime(2026, 11, 4, 10, tzinfo=UTC)
        self.warehouse = WarehouseSnapshot(WarehouseIdVO(uuid4()), True, None)
        self.owner = StockOwnerIdVO(uuid4())
        self.item = InventoryItem.create(
            identifier=InventoryItemIdVO(uuid4()),
            sku=SkuVO("SHIP-ITEM"),
            base_uom=UomCodeVO("KG"),
            quantity_rules=QuantityRulesVO(Decimal("0.05")),
        )
        self.order_ref = ShipmentOrderRefVO("orders", "ORDER-1")
        self.line_ref = ReservationSourceVO("order_line", "ORDER-1/1")
        self.pool = AvailabilityPool.restore(
            identifier=AvailabilityPoolIdVO(uuid4()),
            key=AvailabilityPoolKeyVO(self.item.id, self.warehouse.id, self.owner),
            base_uom=self.item.base_uom,
            eligible_qty=QuantityVO(Decimal(10)),
            reserved_qty=QuantityVO(Decimal(7)),
            assessed_on=self.time.date(),
            version=1,
        )
        self.a = self.reservation("4")
        self.b = self.reservation("3")
        self.line_a = self.line("3", self.a)
        self.line_b = self.line("2", self.b)
        self.order = ShipmentOrderSnapshot(
            self.order_ref,
            True,
            (
                ShipmentOrderLineSnapshot(
                    self.line_ref,
                    self.item.id,
                    self.item.base_uom,
                    QuantityVO(Decimal(7)),
                ),
            ),
        )

    def reservation(self, amount: str) -> StockReservation:
        """Создаёт реальное удержание с отдельной идентичностью под ту же строку заказа."""
        reservation = StockReservation.create(
            identifier=StockReservationIdVO(uuid4()),
            pool=self.pool.reservation_snapshot(),
            inventory_item=self.item.stock_snapshot(),
            source_ref=self.line_ref,
            requested_qty=QuantityVO(Decimal(amount)),
            created_at=self.time - timedelta(hours=1),
            expires_at=self.time + timedelta(hours=1),
        )
        return reservation.add_reserved(
            QuantityVO(Decimal(amount)),
            expected_version=0,
            inventory_item=self.item.stock_snapshot(),
            updated_at=reservation.created_at,
        )

    def line(
        self,
        amount: str = "3",
        reservation: object | None = None,
        **changes: object,
    ) -> ShipmentLine:
        """Создаёт дочерний план по текущему удержанию и системному пересчёту единиц."""
        chosen = self.a if reservation is None else reservation
        return ShipmentLine.create(
            **(
                dict(
                    identifier=ShipmentLineIdVO(uuid4()),
                    inventory_item=self.item.stock_snapshot(),
                    reservation=(
                        chosen.shipment_snapshot()
                        if isinstance(chosen, StockReservation)
                        else chosen
                    ),
                    quantity=QuantityVO(Decimal(amount)),
                    uom=self.item.base_uom,
                )
                | changes
            )
        )

    def create(self, **changes: object) -> Shipment:
        """Создаёт пустой план с явными заказом, складом, владельцем и временем."""
        return Shipment.create(
            **(
                dict(
                    identifier=ShipmentIdVO(uuid4()),
                    order_ref=self.order_ref,
                    warehouse=self.warehouse,
                    owner_id=self.owner,
                    created_at=self.time,
                )
                | changes
            )
        )

    def restore(self, **changes: object) -> Shipment:
        """Восстанавливает собственное историческое состояние без внешних снимков."""
        return Shipment.restore(
            **(
                dict(
                    identifier=ShipmentIdVO(uuid4()),
                    order_ref=self.order_ref,
                    warehouse_id=self.warehouse.id,
                    owner_id=self.owner,
                    status=ShipmentStatus.DRAFT,
                    lines=(),
                    created_at=self.time,
                    updated_at=self.time,
                    version=0,
                )
                | changes
            )
        )

    def add(
        self, shipment: Shipment, line: ShipmentLine | None = None, **changes: object
    ) -> Shipment:
        """Добавляет строку с соответствующим текущим снимком резерва."""
        chosen = self.line_a if line is None else line
        reservation = self.b if chosen.reservation_id == self.b.id else self.a
        return shipment.add_line(
            chosen,
            **(
                dict(
                    expected_version=shipment.version,
                    inventory_item=self.item.stock_snapshot(),
                    reservation=reservation.shipment_snapshot(),
                    updated_at=self.time,
                )
                | changes
            ),
        )

    def draft(self) -> Shipment:
        """Готовит план двух строк 3+2 KG с двумя разными удержаниями."""
        return self.add(self.add(self.create()), self.line_b)

    def change(self, shipment: Shipment, **changes: object) -> Shipment:
        """Меняет количество первой строки, сохраняя её привязку и единицу."""
        return shipment.change_line_quantity(
            **(
                dict(
                    identifier=self.line_a.id,
                    quantity=QuantityVO(Decimal(2)),
                    uom=self.item.base_uom,
                    expected_version=shipment.version,
                    inventory_item=self.item.stock_snapshot(),
                    reservation=self.a.shipment_snapshot(),
                    updated_at=self.time,
                )
                | changes
            )
        )

    def remove(self, shipment: Shipment, **changes: object) -> Shipment:
        """Удаляет первую строку черновика без изменения её удержания."""
        return shipment.remove_line(
            **(
                dict(
                    identifier=self.line_a.id,
                    expected_version=shipment.version,
                    updated_at=self.time,
                )
                | changes
            )
        )

    def confirm(self, shipment: Shipment, **changes: object) -> Shipment:
        """Подтверждает план по снимку заказа и ровно участвующим удержаниям."""
        wanted = {line.reservation_id for line in shipment.lines}
        return shipment.confirm(
            **(
                dict(
                    expected_version=shipment.version,
                    warehouse=self.warehouse,
                    order=self.order,
                    inventory_items=(self.item.stock_snapshot(),),
                    reservations=tuple(
                        value.shipment_snapshot()
                        for value in (self.a, self.b)
                        if value.id in wanted
                    ),
                    updated_at=self.time,
                )
                | changes
            )
        )

    def cancel(self, shipment: Shipment, **changes: object) -> Shipment:
        """Отменяет черновик по ожидаемой версии и явному времени."""
        return shipment.cancel(
            **(dict(expected_version=shipment.version, updated_at=self.time) | changes)
        )

    def test_order_reference_is_normalized_typed_and_immutable(self) -> None:
        """Ссылка заказа сохраняет регистр/нули, запрещает пустоту и управляющие символы."""
        value = ShipmentOrderRefVO(" Orders ", " 001/AbC ")
        self.assertEqual((value.system, value.reference), ("Orders", "001/AbC"))
        self.assertNotEqual(value, ShipmentOrderRefVO("orders", "001/abc"))
        for field in ("system", "reference"):
            for raw in (None, 1, "", "  ", "a\nb", "a\u200bb"):
                with self.assertRaises(InvalidShipmentOrderRefError):
                    replace(value, **{field: raw})
        with self.assertRaises(FrozenInstanceError):
            value.reference = "OTHER"

    def test_create_is_empty_draft_and_requires_active_warehouse(self) -> None:
        """Создание фиксирует только план версии 0, не меняя удержания и общий пул."""
        shipment = self.create()
        self.assertEqual(
            (shipment.status, shipment.lines, shipment.version, shipment.updated_at),
            (ShipmentStatus.DRAFT, (), 0, self.time),
        )
        with self.assertRaises(WarehouseInactiveError):
            self.create(warehouse=replace(self.warehouse, is_active=False))
        with self.assertRaises(InvalidWarehouseSnapshotError):
            self.create(warehouse=None)
        self.assertEqual(
            (
                self.a.reserved_qty.value,
                self.b.reserved_qty.value,
                self.pool.reserved_qty.value,
            ),
            (Decimal(4), Decimal(3), Decimal(7)),
        )

    def test_reservation_snapshot_is_minimal_frozen_and_checks_original(self) -> None:
        """Новый снимок содержит данные для планирования и не изменяет старый контракт исполнения."""
        snapshot = self.a.shipment_snapshot()
        snapshot.ensure_valid()
        self.assertEqual(
            set(snapshot.__dataclass_fields__),
            {
                "id",
                "pool_id",
                "key",
                "source_ref",
                "base_uom",
                "reserved_qty",
                "status",
                "expires_at",
                "updated_at",
                "version",
            },
        )
        self.assertEqual(
            set(self.a.execution_snapshot().__dataclass_fields__),
            {"id", "pool_id", "key", "base_uom", "version"},
        )
        with self.assertRaises(FrozenInstanceError):
            snapshot.reserved_qty = QuantityVO(Decimal(0))
        with self.assertRaises(InvalidStockReservationValueError):
            replace(self.a, version=True).shipment_snapshot()

    def test_line_converts_input_and_derives_identity_from_reservation(self) -> None:
        """3000 G становятся 3 KG с сохранением исходного ввода и привязки к удержанию."""
        line = self.line("3000", uom=UomCodeVO("G"))
        self.assertEqual(
            (
                line.planned_qty.value,
                line.conversion.quantity.value,
                line.conversion.uom.value,
                line.conversion.factor_to_base,
            ),
            (Decimal(3), Decimal(3000), "G", Decimal("0.001")),
        )
        self.assertEqual(
            (
                line.source_ref,
                line.reservation_id,
                line.inventory_item_id,
                line.base_uom,
            ),
            (self.a.source_ref, self.a.id, self.item.id, self.item.base_uom),
        )
        with self.assertRaises(FrozenInstanceError):
            line.planned_qty = QuantityVO(Decimal(1))

    def test_line_quantity_is_positive_multiple_and_not_above_current_hold(
        self,
    ) -> None:
        """Нельзя планировать запрошенное или погашенное количество вместо текущего удержания."""
        with self.assertRaises(ShipmentReservationQuantityExceededError):
            self.line("4.05")
        with self.assertRaises(QuantityStepError):
            self.line("1.23")
        with self.assertRaises(InventoryError):
            self.line("0")
        with self.assertRaises(IncompatibleUomError):
            self.line("1", uom=UomCodeVO("L"))
        consumed = self.a.consume(
            QuantityVO(Decimal(3)),
            expected_version=1,
            inventory_item=self.item.stock_snapshot(),
            consumed_at=self.time,
            updated_at=self.time,
        )
        line = self.line("1", reservation=consumed)
        self.assertEqual(line.planned_qty.value, Decimal(1))
        with self.assertRaises(ShipmentReservationQuantityExceededError):
            self.line("2", reservation=consumed)

    def test_line_restore_preserves_historical_coefficient_and_detects_bad_composition(
        self,
    ) -> None:
        """Восстановление хранит старый коэффициент и не проверяет актуальные удержания."""
        historical = ShipmentLine.restore(
            identifier=self.line_a.id,
            source_ref=self.line_ref,
            reservation_id=self.a.id,
            inventory_item_id=self.item.id,
            base_uom=self.item.base_uom,
            planned_qty=QuantityVO(Decimal(6)),
            shipped_qty=QuantityVO(Decimal(0)),
            conversion=QuantityConversionSnapshotVO(
                QuantityVO(Decimal(3000)), UomCodeVO("G"), Decimal("0.002")
            ),
        )
        self.assertEqual(historical.conversion.factor_to_base, Decimal("0.002"))
        restored = self.restore(
            status=ShipmentStatus.CONFIRMED, lines=(historical,), version=9
        )
        self.assertEqual(restored.lines[0].planned_qty.value, Decimal(6))
        with self.assertRaises(QuantityConversionMismatchError):
            self.confirm(self.restore(lines=(historical,)))
        with self.assertRaises(QuantityConversionMismatchError):
            replace(self.line_a, planned_qty=QuantityVO(Decimal(2))).ensure_valid()

    def test_line_creation_requires_specialized_snapshots_and_matching_item_unit(
        self,
    ) -> None:
        """Полные корни и снимки иного назначения не подменяют контракт строки."""
        with self.assertRaises(InvalidInventoryItemStockSnapshotError):
            self.line(inventory_item=self.item)
        with self.assertRaises(InvalidStockReservationShipmentSnapshotError):
            self.line(reservation=self.a.execution_snapshot())
        with self.assertRaises(ShipmentItemMismatchError):
            self.line(
                inventory_item=replace(
                    self.item.stock_snapshot(),
                    inventory_item_id=InventoryItemIdVO(uuid4()),
                )
            )
        with self.assertRaises(ShipmentUomMismatchError):
            self.line(
                inventory_item=replace(
                    self.item.stock_snapshot(), base_uom=UomCodeVO("G")
                )
            )

    def test_add_change_remove_use_new_versions_and_keep_bindings(self) -> None:
        """Изменения сохраняют область и ссылки, меняя только план и исходный ввод количества."""
        draft = self.add(self.create())
        changed = self.change(
            draft, quantity=QuantityVO(Decimal(2000)), uom=UomCodeVO("G")
        )
        self.assertEqual(
            (changed.version, changed.lines[0].planned_qty.value), (2, Decimal(2))
        )
        for field in (
            "id",
            "source_ref",
            "reservation_id",
            "inventory_item_id",
            "base_uom",
        ):
            self.assertEqual(
                getattr(changed.lines[0], field), getattr(self.line_a, field)
            )
        empty = self.remove(changed)
        self.assertEqual(
            (empty.lines, empty.version, draft.lines[0].planned_qty.value),
            ((), 3, Decimal(3)),
        )

    def test_quantity_edit_can_repair_legacy_step_or_shrunken_hold(self) -> None:
        """Старый план можно уменьшить по новым ограничениям, не меняя его привязку."""
        legacy = replace(
            self.line_a,
            planned_qty=QuantityVO(Decimal("1.23")),
            conversion=QuantityConversionSnapshotVO(
                QuantityVO(Decimal("1.23")), self.item.base_uom, Decimal(1)
            ),
        )
        draft = self.restore(lines=(legacy,))
        fixed = self.change(
            draft,
            quantity=QuantityVO(Decimal("1.20")),
            inventory_item=replace(
                self.item.stock_snapshot(),
                quantity_rules=QuantityRulesVO(Decimal("0.1")),
            ),
        )
        self.assertEqual(fixed.lines[0].planned_qty.value, Decimal("1.20"))
        with self.assertRaises(QuantityStepError):
            self.confirm(draft)
        shrunk = replace(
            self.a.shipment_snapshot(), reserved_qty=QuantityVO(Decimal(2))
        )
        fixed = self.change(self.add(self.create()), reservation=shrunk)
        self.assertEqual(fixed.lines[0].planned_qty.value, Decimal(2))

    def test_quantity_edit_cannot_reassign_reservation_source_item_or_base_unit(
        self,
    ) -> None:
        """Редактирование количества не является заменой товарной строки или основания."""
        draft = self.add(self.create())
        for reservation in (
            self.b.shipment_snapshot(),
            replace(
                self.a.shipment_snapshot(),
                source_ref=ReservationSourceVO("order_line", "OTHER"),
            ),
        ):
            with self.assertRaises(ShipmentReservationMismatchError):
                self.change(draft, reservation=reservation)
        with self.assertRaises(ShipmentItemMismatchError):
            self.change(
                draft,
                inventory_item=replace(
                    self.item.stock_snapshot(),
                    inventory_item_id=InventoryItemIdVO(uuid4()),
                ),
            )
        with self.assertRaises(ShipmentUomMismatchError):
            self.change(
                draft,
                inventory_item=replace(
                    self.item.stock_snapshot(), base_uom=UomCodeVO("G")
                ),
            )

    def test_equal_input_is_noop_only_after_all_current_checks(self) -> None:
        """Равное число в той же единице не меняет время/версию, но не обходит срок резерва."""
        draft = self.add(self.create())
        unchanged = self.change(
            draft,
            quantity=QuantityVO(Decimal("3.000")),
            updated_at=self.time + timedelta(minutes=1),
        )
        self.assertIs(unchanged, draft)
        with self.assertRaises(ShipmentReservationUnavailableError):
            self.change(
                draft, quantity=QuantityVO(Decimal(3)), updated_at=self.a.expires_at
            )
        other_unit = self.change(
            draft, quantity=QuantityVO(Decimal(3000)), uom=UomCodeVO("G")
        )
        self.assertEqual(other_unit.version, 2)

    def test_one_reservation_and_line_id_can_appear_only_once(self) -> None:
        """Разные строки одного заказа допустимы, повтор одного удержания внутри Shipment запрещён."""
        draft = self.add(self.create())
        for line in (
            self.line_a,
            replace(self.line_a, id=ShipmentLineIdVO(uuid4())),
            replace(self.line_b, id=self.line_a.id),
        ):
            with self.assertRaises(ShipmentLineConflictError):
                self.add(draft, line)
        self.assertEqual(len(self.draft().lines), 2)

    def test_unknown_and_raw_line_identifiers_are_rejected(self) -> None:
        """Изменение и удаление требуют ID существующей строки именно этого плана."""
        draft = self.add(self.create())
        for operation in (self.change, self.remove):
            with self.assertRaises(ShipmentLineNotFoundError):
                operation(draft, identifier=ShipmentLineIdVO(uuid4()))
            with self.assertRaises(InvalidShipmentLineError):
                operation(draft, identifier=uuid4())

    def test_confirmation_sums_same_order_line_across_different_reservations(
        self,
    ) -> None:
        """План 3+2 по лимиту 7 подтверждается, даже если заказ имеет другие неотгружаемые строки."""
        draft = self.draft()
        extra = ShipmentOrderLineSnapshot(
            ReservationSourceVO("order_line", "ORDER-1/2"),
            InventoryItemIdVO(uuid4()),
            self.item.base_uom,
            QuantityVO(Decimal(100)),
        )
        confirmed = self.confirm(
            draft, order=replace(self.order, lines=(*self.order.lines, extra))
        )
        self.assertEqual(
            (confirmed.status, confirmed.version, confirmed.lines),
            (ShipmentStatus.CONFIRMED, 3, draft.lines),
        )
        self.assertEqual(
            (
                self.a.reserved_qty.value,
                self.b.reserved_qty.value,
                self.pool.reserved_qty.value,
            ),
            (Decimal(4), Decimal(3), Decimal(7)),
        )

    def test_order_line_limit_is_aggregate_sum_not_each_reservation_limit(self) -> None:
        """Две строки по 3 KG не проходят лимит заказа 5, хотя каждый резерв допускает свой план."""
        draft = self.add(self.add(self.create()), self.line("3", self.b))
        limited = replace(
            self.order,
            lines=(
                replace(
                    self.order.lines[0], remaining_to_ship_qty=QuantityVO(Decimal(5))
                ),
            ),
        )
        with self.assertRaises(ShipmentOrderQuantityExceededError):
            self.confirm(draft, order=limited)
        for remaining in (Decimal(0), Decimal("4.95")):
            order = replace(
                self.order,
                lines=(
                    replace(
                        self.order.lines[0], remaining_to_ship_qty=QuantityVO(remaining)
                    ),
                ),
            )
            with self.assertRaises(ShipmentOrderQuantityExceededError):
                self.confirm(self.draft(), order=order)

    def test_confirmation_rechecks_current_hold_and_expiration(self) -> None:
        """Старый черновик не подтверждается по уменьшенному или истёкшему удержанию."""
        draft = self.add(self.create())
        with self.assertRaises(ShipmentReservationQuantityExceededError):
            self.confirm(
                draft,
                reservations=(
                    replace(
                        self.a.shipment_snapshot(), reserved_qty=QuantityVO(Decimal(2))
                    ),
                ),
            )
        for moment in (self.a.expires_at, self.a.expires_at + timedelta(seconds=1)):
            with self.assertRaises(ShipmentReservationUnavailableError):
                self.confirm(draft, updated_at=moment)
        confirmed = self.confirm(
            draft, updated_at=self.a.expires_at - timedelta(microseconds=1)
        )
        self.assertEqual(confirmed.status, ShipmentStatus.CONFIRMED)

    def test_pending_terminal_and_zero_partial_consumed_reservations_are_unavailable(
        self,
    ) -> None:
        """План опирается на положительное текущее удержание, а не на статус исполнения заказа."""
        for reservation in (
            replace(
                self.a,
                reserved_qty=QuantityVO(Decimal(0)),
                status=StockReservationStatus.PENDING,
            ),
            self.a.release_all(expected_version=1, updated_at=self.time),
            self.a.expire(expected_version=1, updated_at=self.a.expires_at),
            self.a.consume(
                QuantityVO(Decimal(4)),
                expected_version=1,
                inventory_item=self.item.stock_snapshot(),
                consumed_at=self.time,
                updated_at=self.time,
            ),
        ):
            with self.assertRaises(ShipmentReservationUnavailableError):
                self.line("1", reservation=reservation)

    def test_scope_and_future_reservation_snapshot_are_rejected(self) -> None:
        """План одного склада и владельца не принимает чужое или ещё не наступившее состояние резерва."""
        draft = self.create()
        for key in (
            replace(self.a.key, warehouse_id=WarehouseIdVO(uuid4())),
            replace(self.a.key, owner_id=StockOwnerIdVO(uuid4())),
        ):
            with self.assertRaises(ShipmentReservationMismatchError):
                self.add(
                    draft, reservation=replace(self.a.shipment_snapshot(), key=key)
                )
        with self.assertRaises(ShipmentTimeError):
            self.add(
                draft,
                reservation=replace(
                    self.a.shipment_snapshot(),
                    updated_at=self.time + timedelta(seconds=1),
                ),
            )

    def test_order_identity_availability_membership_item_and_unit_are_required(
        self,
    ) -> None:
        """Заказ подтверждает принадлежность строки; совпадения товара самого по себе недостаточно."""
        draft = self.add(self.create())
        for order, error in (
            (
                replace(self.order, order_ref=ShipmentOrderRefVO("orders", "OTHER")),
                InvalidShipmentContextError,
            ),
            (replace(self.order, is_fulfillable=False), ShipmentOrderUnavailableError),
            (replace(self.order, lines=()), InvalidShipmentContextError),
            (
                replace(
                    self.order,
                    lines=(
                        replace(
                            self.order.lines[0],
                            source_ref=ReservationSourceVO("order_line", "OTHER/1"),
                        ),
                    ),
                ),
                InvalidShipmentContextError,
            ),
            (
                replace(
                    self.order,
                    lines=(
                        replace(
                            self.order.lines[0],
                            inventory_item_id=InventoryItemIdVO(uuid4()),
                        ),
                    ),
                ),
                InvalidShipmentContextError,
            ),
            (
                replace(
                    self.order,
                    lines=(replace(self.order.lines[0], base_uom=UomCodeVO("G")),),
                ),
                InvalidShipmentContextError,
            ),
        ):
            with self.assertRaises(error):
                self.confirm(draft, order=order)

    def test_confirmation_requires_exact_unique_item_and_reservation_context(
        self,
    ) -> None:
        """Лишние, отсутствующие или повторные снимки не игнорируются при подтверждении."""
        draft = self.add(self.create())
        for changes in (
            dict(inventory_items=()),
            dict(inventory_items=[]),
            dict(
                inventory_items=(self.item.stock_snapshot(), self.item.stock_snapshot())
            ),
            dict(
                inventory_items=(
                    self.item.stock_snapshot(),
                    replace(
                        self.item.stock_snapshot(),
                        inventory_item_id=InventoryItemIdVO(uuid4()),
                    ),
                )
            ),
            dict(reservations=()),
            dict(reservations=[]),
            dict(reservations=(self.a.shipment_snapshot(), self.a.shipment_snapshot())),
            dict(reservations=(self.a.shipment_snapshot(), self.b.shipment_snapshot())),
        ):
            with self.assertRaises(InvalidShipmentContextError):
                self.confirm(draft, **changes)
        with self.assertRaises(InvalidInventoryItemStockSnapshotError):
            self.confirm(draft, inventory_items=(self.item,))
        with self.assertRaises(InvalidStockReservationShipmentSnapshotError):
            self.confirm(draft, reservations=(self.a,))

    def test_empty_plan_and_inactive_or_foreign_warehouse_cannot_confirm(self) -> None:
        """Подтверждение требует непустой план и тот же активный склад."""
        with self.assertRaises(EmptyShipmentError):
            self.confirm(self.create())
        draft = self.add(self.create())
        with self.assertRaises(WarehouseInactiveError):
            self.confirm(draft, warehouse=replace(self.warehouse, is_active=False))
        with self.assertRaises(InvalidShipmentContextError):
            self.confirm(
                draft, warehouse=replace(self.warehouse, id=WarehouseIdVO(uuid4()))
            )

    def test_only_draft_can_change_confirm_or_cancel(self) -> None:
        """Подтверждённый и отменённый планы неизменяемы; повторное подтверждение и отмена запрещены."""
        for closed in (
            self.confirm(self.add(self.create())),
            self.cancel(self.add(self.create())),
        ):
            for operation in (
                self.add,
                self.change,
                self.remove,
                self.confirm,
                self.cancel,
            ):
                with self.assertRaises(ShipmentStatusError):
                    operation(closed)
        cancelled = self.cancel(self.create())
        self.assertEqual(
            (cancelled.status, cancelled.lines, cancelled.version),
            (ShipmentStatus.CANCELLED, (), 1),
        )

    def test_strict_versions_are_checked_for_every_transition(self) -> None:
        """Версия не принимает bool и должна точно соответствовать текущему состоянию."""
        draft = self.add(self.create())
        for operation in (
            self.add,
            self.change,
            self.remove,
            self.confirm,
            self.cancel,
        ):
            for value in (True, False, -1, None, "1", Decimal(1), 1.0):
                with self.assertRaises(InvalidShipmentValueError):
                    operation(draft, expected_version=value)
            for value in (0, 2):
                with self.assertRaises(ShipmentVersionConflictError):
                    operation(draft, expected_version=value)
        with patch.object(
            ShipmentConfirmationPolicy,
            "ensure_confirmable",
            side_effect=RuntimeError("Не подтверждать"),
        ):
            with self.assertRaises(ShipmentVersionConflictError):
                self.confirm(draft, expected_version=0)

    def test_time_normalizes_to_utc_and_never_regresses(self) -> None:
        """Aware-время сохраняет момент, naive/строки/обратная хронология не принимаются."""
        east = timezone(timedelta(hours=3))
        draft = self.create(created_at=self.time.astimezone(east))
        self.assertIs(draft.created_at.tzinfo, UTC)
        later = self.add(draft, updated_at=self.time + timedelta(minutes=1))
        self.assertEqual(later.updated_at, self.time + timedelta(minutes=1))
        for operation in (self.change, self.remove, self.confirm, self.cancel):
            for value in (None, "now", self.time.replace(tzinfo=None), self.time):
                with self.assertRaises(ShipmentTimeError):
                    operation(later, updated_at=value)
        for value in (
            None,
            "now",
            self.time.replace(tzinfo=None),
            datetime.min.replace(tzinfo=timezone(timedelta(hours=14))),
        ):
            with self.assertRaises(ShipmentTimeError):
                self.create(created_at=value)

    def test_restore_validates_own_state_without_current_context(self) -> None:
        """Исторический подтверждённый план восстанавливается без заказа и актуального состояния резервов."""
        restored = self.restore(
            status=ShipmentStatus.CONFIRMED,
            lines=(self.line_a,),
            created_at=datetime(2020, 1, 1, tzinfo=UTC),
            updated_at=datetime(2020, 1, 2, tzinfo=UTC),
            version=10,
        )
        self.assertEqual((restored.lines, restored.version), ((self.line_a,), 10))
        for changes in (
            dict(identifier=uuid4()),
            dict(order_ref=None),
            dict(warehouse_id=uuid4()),
            dict(owner_id=None),
            dict(status="DRAFT"),
            dict(lines=[]),
            dict(version=True),
            dict(version=-1),
        ):
            with self.assertRaises(InvalidShipmentValueError):
                self.restore(**changes)
        with self.assertRaises(EmptyShipmentError):
            self.restore(status=ShipmentStatus.CONFIRMED)
        with self.assertRaises(ShipmentLineConflictError):
            self.restore(
                lines=(self.line_a, replace(self.line_a, id=ShipmentLineIdVO(uuid4())))
            )
        with self.assertRaises(ShipmentTimeError):
            self.restore(updated_at=self.time - timedelta(seconds=1))

    def test_order_snapshot_is_immutable_and_revalidated_by_consumer(self) -> None:
        """Снимок заказа проверяет типы, уникальность ссылок и неотрицательный остаток."""
        self.order.ensure_valid()
        with self.assertRaises(FrozenInstanceError):
            self.order.is_fulfillable = False
        draft = self.add(self.create())
        for order in (
            None,
            replace(self.order, order_ref=None),
            replace(self.order, is_fulfillable=1),
            replace(self.order, lines=[]),
            replace(self.order, lines=(self.order.lines[0], self.order.lines[0])),
            replace(self.order, lines=({},)),
        ):
            with self.assertRaises(InvalidShipmentOrderSnapshotError):
                self.confirm(draft, order=order)
        for changes in (
            dict(source_ref="ORDER/1"),
            dict(inventory_item_id=uuid4()),
            dict(base_uom="KG"),
            dict(remaining_to_ship_qty=Decimal(7)),
        ):
            with self.assertRaises(InvalidShipmentOrderSnapshotError):
                self.confirm(
                    draft,
                    order=replace(
                        self.order, lines=(replace(self.order.lines[0], **changes),)
                    ),
                )

    def test_reservation_snapshot_is_revalidated_including_status_and_time(
        self,
    ) -> None:
        """Снимок удержания не доверяет аннотациям, bool-версии или несовместимым собственным полям."""
        snapshot = self.a.shipment_snapshot()
        for changes in (
            dict(id=uuid4()),
            dict(pool_id=uuid4()),
            dict(key={}),
            dict(source_ref=None),
            dict(base_uom="KG"),
            dict(reserved_qty=Decimal(4)),
            dict(status="RESERVED"),
            dict(updated_at=self.time.replace(tzinfo=None)),
            dict(expires_at="later"),
            dict(version=True),
            dict(version=-1),
            dict(status=StockReservationStatus.RELEASED),
            dict(reserved_qty=QuantityVO(Decimal(0))),
        ):
            with self.assertRaises(InvalidStockReservationShipmentSnapshotError):
                self.line(reservation=replace(snapshot, **changes))
        with self.assertRaises(UnknownUomError):
            self.line(reservation=replace(snapshot, base_uom=UomCodeVO("BOX")))

    def test_current_confirmation_rules_can_be_repaired_or_removed_in_draft(
        self,
    ) -> None:
        """Изменившийся шаг не делает черновик навсегда неустранимым."""
        line = self.line("1.25")
        draft = self.add(self.create(), line)
        item = replace(
            self.item.stock_snapshot(), quantity_rules=QuantityRulesVO(Decimal("0.1"))
        )
        with self.assertRaises(QuantityStepError):
            self.confirm(draft, inventory_items=(item,))
        fixed = self.change(
            draft,
            identifier=line.id,
            quantity=QuantityVO(Decimal("1.2")),
            inventory_item=item,
        )
        self.assertEqual(
            self.confirm(fixed, inventory_items=(item,)).status,
            ShipmentStatus.CONFIRMED,
        )
        self.assertEqual(self.remove(draft, identifier=line.id).lines, ())

    def test_serial_plans_allow_many_whole_instances_without_selecting_serials(
        self,
    ) -> None:
        """Для SERIAL и LOT_AND_SERIAL план 12 PCS допустим, дробь и другая размерность нет."""
        for mode in (TrackingMode.SERIAL, TrackingMode.LOT_AND_SERIAL):
            item = InventoryItem.create(
                identifier=InventoryItemIdVO(uuid4()),
                sku=SkuVO("SERIAL"),
                base_uom=UomCodeVO("PCS"),
                quantity_rules=QuantityRulesVO(Decimal(1)),
                tracking_mode=mode,
            )
            pool = replace(
                self.pool,
                key=replace(self.pool.key, inventory_item_id=item.id),
                base_uom=item.base_uom,
            )
            reservation = StockReservation.create(
                identifier=StockReservationIdVO(uuid4()),
                pool=pool.reservation_snapshot(),
                inventory_item=item.stock_snapshot(),
                source_ref=self.line_ref,
                requested_qty=QuantityVO(Decimal(12)),
                created_at=self.time,
            )
            reservation = reservation.add_reserved(
                QuantityVO(Decimal(12)),
                expected_version=0,
                inventory_item=item.stock_snapshot(),
                updated_at=self.time,
            )
            line = self.line(
                "12",
                inventory_item=item.stock_snapshot(),
                reservation=reservation.shipment_snapshot(),
                uom=item.base_uom,
            )
            draft = self.add(
                self.create(),
                line,
                inventory_item=item.stock_snapshot(),
                reservation=reservation.shipment_snapshot(),
            )
            order = replace(
                self.order,
                lines=(
                    ShipmentOrderLineSnapshot(
                        self.line_ref, item.id, item.base_uom, QuantityVO(Decimal(12))
                    ),
                ),
            )
            self.assertEqual(
                self.confirm(
                    draft,
                    order=order,
                    inventory_items=(item.stock_snapshot(),),
                    reservations=(reservation.shipment_snapshot(),),
                ).status,
                ShipmentStatus.CONFIRMED,
            )
            with self.assertRaises(QuantityStepError):
                self.line(
                    "0.5",
                    inventory_item=item.stock_snapshot(),
                    reservation=reservation.shipment_snapshot(),
                    uom=item.base_uom,
                )

    def test_all_dimensions_use_common_conversion_and_explicit_step(self) -> None:
        """Объём, длина и площадь используют тот же системный пересчёт, что и масса."""
        for base, input_uom, amount, expected in (
            ("L", "ML", "1500", "1.5"),
            ("M", "CM", "150", "1.5"),
            ("M2", "DM2", "150", "1.5"),
            ("PCS", "PCS", "2", "2"),
        ):
            item = replace(self.item, base_uom=UomCodeVO(base))
            reservation = replace(self.a, base_uom=item.base_uom)
            line = self.line(
                amount,
                inventory_item=item.stock_snapshot(),
                reservation=reservation.shipment_snapshot(),
                uom=UomCodeVO(input_uom),
            )
            self.assertEqual(line.planned_qty.value, Decimal(expected))

    def test_hostile_decimal_context_does_not_round_conversion_or_order_sum(
        self,
    ) -> None:
        """Пересчёт и сумма одной строки заказа не зависят от внешних precision/traps."""
        huge = Decimal("12345678901234567890.10")
        a = replace(
            self.a, requested_qty=QuantityVO(huge), reserved_qty=QuantityVO(huge)
        )
        b = replace(
            self.b,
            requested_qty=QuantityVO(Decimal("0.05")),
            reserved_qty=QuantityVO(Decimal("0.05")),
        )
        with localcontext() as context:
            context.prec = 2
            context.Emax = 2
            context.Emin = -2
            context.traps[Inexact] = True
            context.traps[Rounded] = True
            line_a = self.line(str(huge), reservation=a)
            line_b = self.line("0.05", reservation=b)
            draft = self.add(
                self.add(self.create(), line_a, reservation=a.shipment_snapshot()),
                line_b,
                reservation=b.shipment_snapshot(),
            )
            order = replace(
                self.order,
                lines=(
                    replace(
                        self.order.lines[0],
                        remaining_to_ship_qty=QuantityVO(
                            Decimal("12345678901234567890.15")
                        ),
                    ),
                ),
            )
            confirmed = self.confirm(
                draft,
                order=order,
                reservations=(a.shipment_snapshot(), b.shipment_snapshot()),
            )
            self.assertEqual(confirmed.status, ShipmentStatus.CONFIRMED)
            self.assertFalse(any(context.flags.values()))

    def test_unrepresentable_order_sum_is_controlled_domain_error(self) -> None:
        """Предел точной арифметики не допускает молчаливое округление общей заявки по строке заказа."""
        a = replace(
            self.a,
            requested_qty=QuantityVO(Decimal("1E+1000001")),
            reserved_qty=QuantityVO(Decimal("1E+1000001")),
        )
        line = self.line("1E+1000001", reservation=a)
        draft = self.add(
            self.add(self.create(), line, reservation=a.shipment_snapshot()),
            self.line_b,
        )
        order = replace(
            self.order,
            lines=(
                replace(
                    self.order.lines[0],
                    remaining_to_ship_qty=QuantityVO(Decimal("2E+1000001")),
                ),
            ),
        )
        with self.assertRaises(StockQuantityArithmeticError):
            self.confirm(
                draft,
                order=order,
                reservations=(a.shipment_snapshot(), self.b.shipment_snapshot()),
            )

    def test_confirmation_policy_validates_duplicate_lines_when_called_directly(
        self,
    ) -> None:
        """Чистая Policy не полагается только на фабрику корня для защиты от дублирования удержаний."""
        with self.assertRaises(ShipmentLineConflictError):
            ShipmentConfirmationPolicy.ensure_confirmable(
                order_ref=self.order_ref,
                warehouse_id=self.warehouse.id,
                owner_id=self.owner,
                lines=(self.line_a, replace(self.line_a, id=ShipmentLineIdVO(uuid4()))),
                warehouse=self.warehouse,
                order=self.order,
                inventory_items=(self.item.stock_snapshot(),),
                reservations=(self.a.shipment_snapshot(),),
                as_of=self.time,
            )

    def test_scope_is_local_and_does_not_claim_cross_shipment_allocation_lock(
        self,
    ) -> None:
        """Два независимых плана могут пройти по одному снимку; их общее назначение проверит хранение."""
        first = self.confirm(self.add(self.create()))
        second = self.confirm(self.add(self.create()))
        self.assertNotEqual(first.id, second.id)
        self.assertEqual(first.lines[0].reservation_id, second.lines[0].reservation_id)
        self.assertEqual(self.a.reserved_qty.value, Decimal(4))

    def test_direct_invalid_dataclass_cannot_bypass_domain_methods(self) -> None:
        """Публичные переходы повторно проверяют состав и UTC-хранение собственного агрегата."""
        draft = self.add(self.create())
        for changes, error in (
            (dict(owner_id=None), InvalidShipmentValueError),
            (dict(version=True), InvalidShipmentValueError),
            (dict(lines=(self.line_a, self.line_a)), ShipmentLineConflictError),
            (
                dict(created_at=self.time.astimezone(timezone(timedelta(hours=3)))),
                ShipmentTimeError,
            ),
        ):
            malformed = replace(draft, **changes)
            for operation in (self.change, self.remove, self.confirm, self.cancel):
                with self.assertRaises(error):
                    operation(malformed)

    def test_success_failure_and_cancel_leave_originals_unchanged(self) -> None:
        """Новые версии плана не меняют удержания, потреблённое количество или общий пул."""
        draft = self.draft()
        before = (self.a, self.b, self.pool)
        confirmed = self.confirm(draft)
        cancelled = self.cancel(draft)
        with self.assertRaises(ShipmentReservationQuantityExceededError):
            self.change(draft, quantity=QuantityVO(Decimal(5)))
        self.assertEqual((self.a, self.b, self.pool), before)
        self.assertEqual(draft.status, ShipmentStatus.DRAFT)
        self.assertEqual(cancelled.lines, draft.lines)
        self.assertEqual(confirmed.lines, draft.lines)
        with self.assertRaises(FrozenInstanceError):
            confirmed.status = ShipmentStatus.DRAFT


if __name__ == "__main__":
    unittest.main()
