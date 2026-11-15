from typing import Any
from src.modules.inventory.domain.stock_position.value_object.dimensions import (
    StockDimensionsVO,
)
from src.modules.inventory.domain.stock_position.value_object.identifier import (
    StockPositionIdVO,
)
from src.modules.inventory.domain.inventory_item.value_object.identifier import (
    InventoryItemIdVO,
)
from src.modules.inventory.domain.stock_location.value_object.identifier import (
    StockLocationIdVO,
)
from src.modules.inventory.domain.stock_lot.value_object.identifier import StockLotIdVO
from src.modules.inventory.domain.stock_serial.value_object.identifier import (
    StockSerialIdVO,
)
from src.modules.inventory.domain.value_object.stock_owner_id import StockOwnerIdVO
from src.modules.inventory.domain.value_object.stock_status import StockStatus
from src.modules.inventory.domain.value_object.quantity import QuantityVO
from src.modules.inventory.domain.value_object.uom_code import UomCodeVO
from src.modules.inventory.domain.stock_position.aggregate import StockPosition
from src.modules.inventory.infrastructure.persistence.models.stock_positions import (
    StockPositionModel,
)


class StockPositionMapper:
    """Преобразует полное собственное состояние позиции без SQL и текущих справочников."""

    @staticmethod
    def to_values(position: StockPosition) -> dict[str, Any]:
        """Извлекает точное количество и полный ключ, не генерируя новый ID."""
        dims = position.dimensions
        return dict(
            id=position.id.uuid,
            inventory_item_id=dims.inventory_item_id.uuid,
            location_id=dims.location_id.uuid,
            owner_id=dims.owner_id.uuid,
            lot_id=dims.lot_id.uuid if dims.lot_id else None,
            serial_id=dims.serial_id.uuid if dims.serial_id else None,
            stock_status=dims.stock_status.value,
            base_uom=position.base_uom.value,
            on_hand_qty=position.on_hand_qty.value,
            version=position.version,
        )

    @staticmethod
    def to_domain(model: StockPositionModel) -> StockPosition:
        """Восстанавливает сохранённый остаток с прежней версией и измерениями."""
        return StockPosition.restore(
            identifier=StockPositionIdVO(model.id),
            dimensions=StockDimensionsVO(
                InventoryItemIdVO(model.inventory_item_id),
                StockLocationIdVO(model.location_id),
                StockOwnerIdVO(model.owner_id),
                StockLotIdVO(model.lot_id) if model.lot_id else None,
                StockSerialIdVO(model.serial_id) if model.serial_id else None,
                StockStatus(model.stock_status),
            ),
            base_uom=UomCodeVO(model.base_uom),
            on_hand_qty=QuantityVO(model.on_hand_qty),
            version=model.version,
        )
