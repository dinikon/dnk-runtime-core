from src.modules.inventory.application.stock_lot.command.create_stock_lot.command import (
    CreateStockLotCommand,
)
from src.modules.inventory.application.stock_lot.command.create_stock_lot.dto import (
    CreateStockLotResultDTO,
)
from src.modules.inventory.domain.inventory_item.error import InventoryItemNotFoundError
from src.modules.inventory.domain.inventory_item.repository import (
    InventoryItemRepositoryProtocol,
)
from src.modules.inventory.domain.stock_lot.aggregate import StockLot
from src.modules.inventory.domain.stock_lot.repository import StockLotRepositoryProtocol
from src.modules.inventory.domain.stock_lot.value_object.identifier import StockLotIdVO
from src.modules.inventory.domain.stock_lot.value_object.lot_number import LotNumberVO
from src.modules.inventory.domain.value_object.stock_dates import StockDatesVO
from src.modules.shared.application.uuid.uuid_port import UUIdGeneratorProtocol


class CreateStockLotHandler:
    """Создаёт партию по актуальному заблокированному SKU в транзакции внешнего UoW."""

    def __init__(
        self,
        items: InventoryItemRepositoryProtocol,
        lots: StockLotRepositoryProtocol,
        uuid_generator: UUIdGeneratorProtocol,
    ) -> None:
        """Принимает write-порты одной сессии и общий генератор идентификаторов."""
        self._items = items
        self._lots = lots
        self._uuid_generator = uuid_generator

    async def execute(self, command: CreateStockLotCommand) -> CreateStockLotResultDTO:
        """Блокирует товар, передаёт снимок фабрике Domain и сохраняет самостоятельную партию."""
        item = await self._items.get_for_update(command.inventory_item_id)
        if item is None:
            raise InventoryItemNotFoundError("Складская позиция не найдена.")
        lot = StockLot.create(
            identifier=StockLotIdVO.from_value(self._uuid_generator.new()),
            inventory_item=item.tracking_snapshot(),
            number=LotNumberVO(command.number),
            dates=StockDatesVO(command.manufactured_on, command.expires_on),
        )
        await self._lots.add(lot)
        return CreateStockLotResultDTO(
            id=lot.id.uuid,
            inventory_item_id=lot.inventory_item_id.uuid,
            number=lot.number.value,
            manufactured_on=lot.dates.manufactured_on,
            expires_on=lot.dates.expires_on,
        )
