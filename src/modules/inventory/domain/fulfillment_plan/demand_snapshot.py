from dataclasses import dataclass

from src.modules.inventory.domain.fulfillment_plan.error import (
    InvalidFulfillmentDemandError,
)
from src.modules.inventory.domain.fulfillment_plan.value_object.order_ref import (
    FulfillmentOrderRefVO,
)
from src.modules.inventory.domain.inventory_item.value_object.identifier import (
    InventoryItemIdVO,
)
from src.modules.inventory.domain.stock_reservation.value_object.source import (
    ReservationSourceVO,
)
from src.modules.inventory.domain.uom_catalog import get_uom
from src.modules.inventory.domain.value_object.quantity import QuantityVO
from src.modules.inventory.domain.value_object.uom_code import UomCodeVO


@dataclass(frozen=True, slots=True)
class FulfillmentDemandLineSnapshot:
    """Передаёт идентичность строки заказа, её текущую потребность и разрешение разделить источники."""

    source_ref: ReservationSourceVO
    inventory_item_id: InventoryItemIdVO
    base_uom: UomCodeVO
    remaining_qty: QuantityVO
    allow_source_split: bool

    def ensure_valid(self) -> None:
        """Требует типизированные значения, неотрицательную потребность и настоящий bool разрешения."""
        if (
            not isinstance(self.source_ref, ReservationSourceVO)
            or not isinstance(self.inventory_item_id, InventoryItemIdVO)
            or not isinstance(self.base_uom, UomCodeVO)
            or not isinstance(self.remaining_qty, QuantityVO)
            or type(self.allow_source_split) is not bool
        ):
            raise InvalidFulfillmentDemandError(
                "Нужны типизированные значения строки потребности и bool разрешения разделения."
            )
        get_uom(self.base_uom)


@dataclass(frozen=True, slots=True)
class FulfillmentDemandSnapshot:
    """Фиксирует принадлежность строк одному заказу и его доступность без прямой ссылки на Orders."""

    order_ref: FulfillmentOrderRefVO
    is_fulfillable: bool
    lines: tuple[FulfillmentDemandLineSnapshot, ...]

    def ensure_valid(self) -> None:
        """Проверяет номинальные типы, tuple и уникальность непрозрачных ссылок строк."""
        if (
            not isinstance(self.order_ref, FulfillmentOrderRefVO)
            or type(self.is_fulfillable) is not bool
            or not isinstance(self.lines, tuple)
        ):
            raise InvalidFulfillmentDemandError(
                "Нужны ссылка заказа, bool доступности и tuple строк потребности."
            )
        refs = set()
        for line in self.lines:
            if not isinstance(line, FulfillmentDemandLineSnapshot):
                raise InvalidFulfillmentDemandError(
                    "Нужны специализированные снимки строк заказа."
                )
            line.ensure_valid()
            if line.source_ref in refs:
                raise InvalidFulfillmentDemandError(
                    "Ссылка строки повторяется в потребности заказа."
                )
            refs.add(line.source_ref)
