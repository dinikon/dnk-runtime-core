from src.modules.inventory.application.stock_lot.command.update_stock_lot.command import (
    UpdateStockLotCommand,
)
from src.modules.inventory.application.stock_lot.command.update_stock_lot.dto import (
    UpdateStockLotResultDTO,
)
from src.modules.inventory.domain.inventory_item.error import InventoryItemNotFoundError
from src.modules.inventory.domain.inventory_item.repository import (
    InventoryItemRepositoryProtocol,
)
from src.modules.inventory.domain.stock_lot.error import StockLotNotFoundError
from src.modules.inventory.domain.stock_lot.repository import StockLotRepositoryProtocol
from src.modules.inventory.domain.value_object.stock_dates import StockDatesVO


class UpdateStockLotHandler:
    """Координирует изменение дат через Domain на актуальном снимке заблокированного SKU."""

    def __init__(
        self, items: InventoryItemRepositoryProtocol, lots: StockLotRepositoryProtocol
    ) -> None:
        """Принимает write-порты одной сессии внешнего tenant-UoW."""
        self._items = items
        self._lots = lots

    async def execute(self, command: UpdateStockLotCommand) -> UpdateStockLotResultDTO:
        """Блокирует SKU до партии, объединяет PATCH и проверяет Domain даже для no-op."""
        item = await self._items.get_for_update(command.inventory_item_id)
        if item is None:
            raise InventoryItemNotFoundError("Складская позиция не найдена.")
        lot = await self._lots.get_for_update(command.lot_id, inventory_item_id=item.id)
        if lot is None:
            raise StockLotNotFoundError("Партия не найдена в указанном SKU.")
        dates = StockDatesVO(
            (
                command.manufactured_on
                if "manufactured_on" in command.fields
                else lot.dates.manufactured_on
            ),
            (
                command.expires_on
                if "expires_on" in command.fields
                else lot.dates.expires_on
            ),
        )
        updated = lot.change_dates(dates, inventory_item=item.tracking_snapshot())
        if updated != lot:
            await self._lots.save(updated)
        return UpdateStockLotResultDTO(
            id=updated.id.uuid,
            inventory_item_id=updated.inventory_item_id.uuid,
            number=updated.number.value,
            manufactured_on=updated.dates.manufactured_on,
            expires_on=updated.dates.expires_on,
        )
