from dataclasses import dataclass
from datetime import datetime, timedelta

from src.modules.inventory.domain.inventory_item.value_object.identifier import (
    InventoryItemIdVO,
)
from src.modules.inventory.domain.shipment.error import (
    InvalidShipmentDocumentSnapshotError,
)
from src.modules.inventory.domain.shipment.value_object.identifier import ShipmentIdVO
from src.modules.inventory.domain.shipment.value_object.line_id import ShipmentLineIdVO
from src.modules.inventory.domain.shipment.value_object.status import ShipmentStatus
from src.modules.inventory.domain.uom_catalog import get_uom
from src.modules.inventory.domain.value_object.quantity import QuantityVO
from src.modules.inventory.domain.value_object.stock_owner_id import StockOwnerIdVO
from src.modules.inventory.domain.value_object.uom_code import UomCodeVO
from src.modules.inventory.domain.warehouse.value_object.identifier import WarehouseIdVO


@dataclass(frozen=True, slots=True)
class ShipmentDocumentLineSnapshot:
    """Передаёт положительный остаток одной строки отправления в базовой единице."""

    shipment_line_id: ShipmentLineIdVO
    inventory_item_id: InventoryItemIdVO
    base_uom: UomCodeVO
    remaining_qty: QuantityVO

    def ensure_valid(self) -> None:
        """Проверяет собственные типы, известную единицу и строго положительный остаток."""
        if (
            not isinstance(self.shipment_line_id, ShipmentLineIdVO)
            or not isinstance(self.inventory_item_id, InventoryItemIdVO)
            or not isinstance(self.base_uom, UomCodeVO)
            or not isinstance(self.remaining_qty, QuantityVO)
            or self.remaining_qty.value.is_zero()
        ):
            raise InvalidShipmentDocumentSnapshotError(
                "Нужна типизированная строка с положительным остатком к отгрузке."
            )
        get_uom(self.base_uom)


@dataclass(frozen=True, slots=True)
class ShipmentDocumentSnapshot:
    """Передаёт версию и только открытые остатки отправления для построения и подтверждения документа."""

    id: ShipmentIdVO
    version: int
    status: ShipmentStatus
    warehouse_id: WarehouseIdVO
    owner_id: StockOwnerIdVO
    updated_at: datetime
    lines: tuple[ShipmentDocumentLineSnapshot, ...]

    def ensure_valid(self) -> None:
        """Проверяет UTC, строгую версию, уникальность строк и локально проверяемое соответствие статусу."""
        if (
            not isinstance(self.id, ShipmentIdVO)
            or type(self.version) is not int
            or self.version < 0
            or not isinstance(self.status, ShipmentStatus)
            or not isinstance(self.warehouse_id, WarehouseIdVO)
            or not isinstance(self.owner_id, StockOwnerIdVO)
            or not isinstance(self.updated_at, datetime)
            or self.updated_at.utcoffset() != timedelta(0)
            or not isinstance(self.lines, tuple)
        ):
            raise InvalidShipmentDocumentSnapshotError(
                "Нужен типизированный снимок отправления с UTC-временем и целой версией."
            )
        ids = set()
        for line in self.lines:
            if not isinstance(line, ShipmentDocumentLineSnapshot):
                raise InvalidShipmentDocumentSnapshotError(
                    "Нужны снимки открытых строк отправления."
                )
            line.ensure_valid()
            if line.shipment_line_id in ids:
                raise InvalidShipmentDocumentSnapshotError(
                    "Строки отправления не должны повторяться."
                )
            ids.add(line.shipment_line_id)
        if (
            self.status in (ShipmentStatus.CONFIRMED, ShipmentStatus.PARTIALLY_SHIPPED)
            and not self.lines
        ) or (self.status is ShipmentStatus.SHIPPED and self.lines):
            raise InvalidShipmentDocumentSnapshotError(
                "Статус снимка не соответствует открытым остаткам отправления."
            )
