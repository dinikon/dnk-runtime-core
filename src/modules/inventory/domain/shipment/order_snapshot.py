from dataclasses import dataclass

from src.modules.inventory.domain.inventory_item.value_object.identifier import (
    InventoryItemIdVO,
)
from src.modules.inventory.domain.shipment.error import (
    InvalidShipmentOrderSnapshotError,
)
from src.modules.inventory.domain.shipment.value_object.order_ref import (
    ShipmentOrderRefVO,
)
from src.modules.inventory.domain.stock_reservation.value_object.source import (
    ReservationSourceVO,
)
from src.modules.inventory.domain.uom_catalog import get_uom
from src.modules.inventory.domain.value_object.quantity import QuantityVO
from src.modules.inventory.domain.value_object.uom_code import UomCodeVO


@dataclass(frozen=True, slots=True)
class ShipmentOrderLineSnapshot:
    """Передаёт строку заказа, её товар, базовую единицу и неотрицательный остаток к отправке."""

    source_ref: ReservationSourceVO
    inventory_item_id: InventoryItemIdVO
    base_uom: UomCodeVO
    remaining_to_ship_qty: QuantityVO

    def ensure_valid(self) -> None:
        """Проверяет собственные типы и известную единицу без загрузки заказа."""
        if (
            not isinstance(self.source_ref, ReservationSourceVO)
            or not isinstance(self.inventory_item_id, InventoryItemIdVO)
            or not isinstance(self.base_uom, UomCodeVO)
            or not isinstance(self.remaining_to_ship_qty, QuantityVO)
        ):
            raise InvalidShipmentOrderSnapshotError(
                "Нужны типизированные значения строки заказа."
            )
        get_uom(self.base_uom)


@dataclass(frozen=True, slots=True)
class ShipmentOrderSnapshot:
    """Предоставляет принадлежность строк одному заказу и актуальные лимиты подтверждения плана."""

    order_ref: ShipmentOrderRefVO
    is_fulfillable: bool
    lines: tuple[ShipmentOrderLineSnapshot, ...]

    def ensure_valid(self) -> None:
        """Требует типизированный заказ, настоящий bool и уникальные ссылки строк."""
        if (
            not isinstance(self.order_ref, ShipmentOrderRefVO)
            or type(self.is_fulfillable) is not bool
            or not isinstance(self.lines, tuple)
        ):
            raise InvalidShipmentOrderSnapshotError(
                "Нужны ссылка заказа, bool доступности и tuple строк."
            )
        refs = set()
        for line in self.lines:
            if not isinstance(line, ShipmentOrderLineSnapshot):
                raise InvalidShipmentOrderSnapshotError("Нужны снимки строк заказа.")
            line.ensure_valid()
            if line.source_ref in refs:
                raise InvalidShipmentOrderSnapshotError(
                    "Ссылки строк внутри снимка заказа не должны повторяться."
                )
            refs.add(line.source_ref)
