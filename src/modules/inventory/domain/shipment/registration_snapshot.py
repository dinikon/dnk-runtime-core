from dataclasses import dataclass
from datetime import datetime, timedelta

from src.modules.inventory.domain.inventory_item.value_object.identifier import (
    InventoryItemIdVO,
)
from src.modules.inventory.domain.shipment.error import (
    InvalidShipmentExecutionRegistrationSnapshotError,
)
from src.modules.inventory.domain.shipment.value_object.identifier import ShipmentIdVO
from src.modules.inventory.domain.shipment.value_object.line_id import ShipmentLineIdVO
from src.modules.inventory.domain.stock_execution.value_object.identifier import (
    StockExecutionIdVO,
)
from src.modules.inventory.domain.stock_execution.value_object.line_id import (
    StockExecutionLineIdVO,
)
from src.modules.inventory.domain.stock_posting.value_object.operation_type import (
    StockOperationType,
)
from src.modules.inventory.domain.stock_reservation.value_object.execution_binding import (
    ReservationExecutionBindingVO,
)
from src.modules.inventory.domain.stock_reservation.value_object.identifier import (
    StockReservationIdVO,
)
from src.modules.inventory.domain.uom_catalog import get_uom
from src.modules.inventory.domain.value_object.quantity import QuantityVO
from src.modules.inventory.domain.value_object.stock_owner_id import StockOwnerIdVO
from src.modules.inventory.domain.value_object.uom_code import UomCodeVO
from src.modules.inventory.domain.warehouse.value_object.identifier import WarehouseIdVO


@dataclass(frozen=True, slots=True)
class ShipmentExecutionRegistrationLineSnapshot:
    """Сохраняет сумму целых фактических строк для одной строки плана и её резерва."""

    shipment_line_id: ShipmentLineIdVO
    inventory_item_id: InventoryItemIdVO
    base_uom: UomCodeVO
    reservation_id: StockReservationIdVO
    quantity: QuantityVO
    execution_line_ids: tuple[StockExecutionLineIdVO, ...]

    def ensure_valid(self) -> None:
        """Требует положительное количество и непустой уникальный состав типизированных фактических ID."""
        if (
            not isinstance(self.shipment_line_id, ShipmentLineIdVO)
            or not isinstance(self.inventory_item_id, InventoryItemIdVO)
            or not isinstance(self.base_uom, UomCodeVO)
            or not isinstance(self.reservation_id, StockReservationIdVO)
            or not isinstance(self.quantity, QuantityVO)
            or self.quantity.value.is_zero()
            or not isinstance(self.execution_line_ids, tuple)
            or not self.execution_line_ids
            or not all(
                isinstance(value, StockExecutionLineIdVO)
                for value in self.execution_line_ids
            )
        ):
            raise InvalidShipmentExecutionRegistrationSnapshotError(
                "Некорректная строка регистрации отгрузки."
            )
        get_uom(self.base_uom)
        if len(set(self.execution_line_ids)) != len(self.execution_line_ids):
            raise InvalidShipmentExecutionRegistrationSnapshotError(
                "Фактические ID строки не должны повторяться."
            )


@dataclass(frozen=True, slots=True)
class ShipmentExecutionRegistrationSnapshot:
    """Передаёт прогресс по одному факту и версии Shipment вместе с проверенными назначениями резервам."""

    shipment_id: ShipmentIdVO
    shipment_version: int
    execution_id: StockExecutionIdVO
    operation_type: StockOperationType
    warehouse_id: WarehouseIdVO
    owner_id: StockOwnerIdVO
    executed_at: datetime
    lines: tuple[ShipmentExecutionRegistrationLineSnapshot, ...]

    def ensure_valid(self) -> None:
        """Проверяет область, строгую версию, ISSUE, UTC и однократность строк/резервов/фактических ID."""
        if (
            not isinstance(self.shipment_id, ShipmentIdVO)
            or type(self.shipment_version) is not int
            or self.shipment_version < 0
            or not isinstance(self.execution_id, StockExecutionIdVO)
            or self.operation_type is not StockOperationType.ISSUE
            or not isinstance(self.warehouse_id, WarehouseIdVO)
            or not isinstance(self.owner_id, StockOwnerIdVO)
            or not isinstance(self.executed_at, datetime)
            or self.executed_at.utcoffset() != timedelta(0)
            or not isinstance(self.lines, tuple)
            or not self.lines
        ):
            raise InvalidShipmentExecutionRegistrationSnapshotError(
                "Нужен непустой результат ISSUE с типизированными ссылками, версией и UTC-временем."
            )
        ids, reservations, execution_ids = set(), set(), set()
        for line in self.lines:
            if not isinstance(line, ShipmentExecutionRegistrationLineSnapshot):
                raise InvalidShipmentExecutionRegistrationSnapshotError(
                    "Нужны снимки зарегистрированных строк."
                )
            line.ensure_valid()
            if (
                line.shipment_line_id in ids
                or line.reservation_id in reservations
                or execution_ids.intersection(line.execution_line_ids)
            ):
                raise InvalidShipmentExecutionRegistrationSnapshotError(
                    "Плановые строки, резервы и фактические ID не должны повторяться."
                )
            ids.add(line.shipment_line_id)
            reservations.add(line.reservation_id)
            execution_ids.update(line.execution_line_ids)

    def reservation_bindings(self) -> tuple[ReservationExecutionBindingVO, ...]:
        """Выводит существующие привязки погашения из проверенных строк без независимого выбора резерва."""
        self.ensure_valid()
        values = tuple(
            ReservationExecutionBindingVO(identifier, line.reservation_id)
            for line in self.lines
            for identifier in line.execution_line_ids
        )
        return tuple(sorted(values, key=lambda value: value.execution_line_id.uuid.int))
