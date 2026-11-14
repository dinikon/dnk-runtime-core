from typing import Any

from src.modules.inventory.domain.stock_serial.aggregate import StockSerial
from src.modules.inventory.domain.stock_serial.value_object.identifier import (
    StockSerialIdVO,
)
from src.modules.inventory.domain.stock_serial.value_object.serial_number import (
    SerialNumberVO,
)
from src.modules.inventory.domain.stock_lot.value_object.identifier import StockLotIdVO
from src.modules.inventory.domain.inventory_item.value_object.identifier import (
    InventoryItemIdVO,
)
from src.modules.inventory.infrastructure.persistence.models.stock_serial import (
    StockSerialModel,
)


class StockSerialMapper:
    """Преобразует хранение в агрегат и значения записи без SQL и бизнес-проверок."""

    @staticmethod
    def to_domain(model: StockSerialModel) -> StockSerial:
        """Восстанавливает сохранённую идентичность и связь без текущих настроек SKU."""
        return StockSerial.restore(
            identifier=StockSerialIdVO.from_value(model.id),
            inventory_item_id=InventoryItemIdVO.from_value(model.inventory_item_id),
            number=SerialNumberVO(model.number),
            lot_id=(
                StockLotIdVO.from_value(model.lot_id)
                if model.lot_id is not None
                else None
            ),
        )

    @staticmethod
    def to_insert_values(serial: StockSerial) -> dict[str, Any]:
        """Извлекает скаляры без добавления дат или генерации новых ID."""
        return dict(
            id=serial.id.uuid,
            inventory_item_id=serial.inventory_item_id.uuid,
            number=serial.number.value,
            lot_id=serial.lot_id.uuid if serial.lot_id is not None else None,
        )
