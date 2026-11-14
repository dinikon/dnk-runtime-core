from datetime import date
from uuid import UUID

from src.modules.inventory.domain.inventory_item.value_object.identifier import (
    InventoryItemIdVO,
)
from src.modules.inventory.domain.stock_lot.aggregate import StockLot
from src.modules.inventory.domain.stock_lot.value_object.identifier import StockLotIdVO
from src.modules.inventory.domain.stock_lot.value_object.lot_number import LotNumberVO
from src.modules.inventory.domain.value_object.stock_dates import StockDatesVO
from src.modules.inventory.infrastructure.persistence.models.stock_lot import (
    StockLotModel,
)


class StockLotMapper:
    """Преобразует сохранённую модель и агрегат партии без I/O и бизнес-проверок."""

    @staticmethod
    def to_insert_values(lot: StockLot) -> dict[str, UUID | str | date | None]:
        """Сохраняет доменные ID, точный номер и date без времени."""
        return {
            "id": lot.id.uuid,
            "inventory_item_id": lot.inventory_item_id.uuid,
            "number": lot.number.value,
            "manufactured_on": lot.dates.manufactured_on,
            "expires_on": lot.dates.expires_on,
        }

    @staticmethod
    def to_domain(model: StockLotModel) -> StockLot:
        """Восстанавливает собственное состояние партии без текущих правил другого корня."""
        return StockLot.restore(
            identifier=StockLotIdVO.from_value(model.id),
            inventory_item_id=InventoryItemIdVO.from_value(model.inventory_item_id),
            number=LotNumberVO(model.number),
            dates=StockDatesVO(model.manufactured_on, model.expires_on),
        )

    @staticmethod
    def to_update_values(lot: StockLot) -> dict[str, date | None]:
        """Подготавливает только даты, сохраняя неизменными ID, владельца и номер."""
        return {
            "manufactured_on": lot.dates.manufactured_on,
            "expires_on": lot.dates.expires_on,
        }
