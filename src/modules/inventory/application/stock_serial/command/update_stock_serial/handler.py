from src.modules.inventory.application.stock_serial.command.update_stock_serial.command import (
    UpdateStockSerialCommand,
)
from src.modules.inventory.application.stock_serial.command.update_stock_serial.dto import (
    UpdateStockSerialResultDTO,
)
from src.modules.inventory.domain.inventory_item.error import InventoryItemNotFoundError
from src.modules.inventory.domain.inventory_item.repository import (
    InventoryItemRepositoryProtocol,
)
from src.modules.inventory.domain.stock_lot.repository import StockLotRepositoryProtocol
from src.modules.inventory.domain.stock_lot.error import StockLotNotFoundError
from src.modules.inventory.domain.stock_serial.repository import (
    StockSerialRepositoryProtocol,
)
from src.modules.inventory.domain.stock_serial.value_object.serial_number import (
    SerialNumberVO,
)
from src.modules.inventory.domain.stock_serial.error import StockSerialNotFoundError


class UpdateStockSerialHandler:
    """Изменяет идентификацию экземпляра по актуальным снимкам в общей транзакции."""

    def __init__(
        self,
        items: InventoryItemRepositoryProtocol,
        lots: StockLotRepositoryProtocol,
        serials: StockSerialRepositoryProtocol,
    ) -> None:
        """Принимает write-порты одной сессии внешнего tenant-UoW."""
        self._items, self._lots, self._serials = items, lots, serials

    async def execute(
        self, command: UpdateStockSerialCommand
    ) -> UpdateStockSerialResultDTO:
        """Блокирует SKU, экземпляр и целевую партию; проверяет Domain даже для no-op."""
        item = await self._items.get_for_update(command.inventory_item_id)
        if item is None:
            raise InventoryItemNotFoundError("Складская позиция не найдена.")
        serial = await self._serials.get_for_update(
            command.serial_id, inventory_item_id=item.id
        )
        if serial is None:
            raise StockSerialNotFoundError("Экземпляр не найден в указанном SKU.")
        target_lot_id = command.lot_id if "lot_id" in command.fields else serial.lot_id
        lot = None
        if target_lot_id is not None:
            lot = await self._lots.get_for_update(
                target_lot_id, inventory_item_id=item.id
            )
            if lot is None:
                raise StockLotNotFoundError("Партия не найдена в указанном SKU.")
        updated = serial.change_identification(
            SerialNumberVO(
                command.number if "number" in command.fields else serial.number.value
            ),
            inventory_item=item.tracking_snapshot(),
            lot=lot.snapshot() if lot is not None else None,
        )
        if updated != serial:
            await self._serials.save(updated)
        return UpdateStockSerialResultDTO(
            id=updated.id.uuid,
            inventory_item_id=updated.inventory_item_id.uuid,
            number=updated.number.value,
            lot_id=updated.lot_id.uuid if updated.lot_id is not None else None,
            lot_number=lot.number.value if lot is not None else None,
            date_source="LOT" if lot is not None else "NONE",
            manufactured_on=lot.dates.manufactured_on if lot is not None else None,
            expires_on=lot.dates.expires_on if lot is not None else None,
        )
