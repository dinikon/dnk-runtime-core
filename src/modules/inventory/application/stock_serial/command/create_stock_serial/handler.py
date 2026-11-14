from src.modules.inventory.application.stock_serial.command.create_stock_serial.command import (
    CreateStockSerialCommand,
)
from src.modules.inventory.application.stock_serial.command.create_stock_serial.dto import (
    CreateStockSerialResultDTO,
)
from src.modules.inventory.domain.inventory_item.error import InventoryItemNotFoundError
from src.modules.inventory.domain.inventory_item.repository import (
    InventoryItemRepositoryProtocol,
)
from src.modules.inventory.domain.stock_lot.repository import StockLotRepositoryProtocol
from src.modules.inventory.domain.stock_lot.error import StockLotNotFoundError
from src.modules.inventory.domain.stock_serial.aggregate import StockSerial
from src.modules.inventory.domain.stock_serial.repository import (
    StockSerialRepositoryProtocol,
)
from src.modules.inventory.domain.stock_serial.value_object.identifier import (
    StockSerialIdVO,
)
from src.modules.inventory.domain.stock_serial.value_object.serial_number import (
    SerialNumberVO,
)
from src.modules.shared.application.uuid.uuid_port import UUIdGeneratorProtocol


class CreateStockSerialHandler:
    """Создаёт экземпляр по актуальным снимкам товара и партии в общей транзакции."""

    def __init__(
        self,
        items: InventoryItemRepositoryProtocol,
        lots: StockLotRepositoryProtocol,
        serials: StockSerialRepositoryProtocol,
        uuid_generator: UUIdGeneratorProtocol,
    ) -> None:
        """Принимает write-порты одной сессии и генератор идентификаторов."""
        self._items, self._lots, self._serials, self._uuid_generator = (
            items,
            lots,
            serials,
            uuid_generator,
        )

    async def execute(
        self, command: CreateStockSerialCommand
    ) -> CreateStockSerialResultDTO:
        """Блокирует сначала SKU, затем партию, передавая бизнес-проверки фабрике Domain."""
        item = await self._items.get_for_update(command.inventory_item_id)
        if item is None:
            raise InventoryItemNotFoundError("Складская позиция не найдена.")
        lot = None
        if command.lot_id is not None:
            lot = await self._lots.get_for_update(
                command.lot_id, inventory_item_id=item.id
            )
            if lot is None:
                raise StockLotNotFoundError("Партия не найдена в указанном SKU.")
        serial = StockSerial.create(
            identifier=StockSerialIdVO.from_value(self._uuid_generator.new()),
            inventory_item=item.tracking_snapshot(),
            number=SerialNumberVO(command.number),
            lot=lot.snapshot() if lot is not None else None,
        )
        await self._serials.add(serial)
        return CreateStockSerialResultDTO(
            id=serial.id.uuid,
            inventory_item_id=serial.inventory_item_id.uuid,
            number=serial.number.value,
            lot_id=serial.lot_id.uuid if serial.lot_id is not None else None,
            lot_number=lot.number.value if lot is not None else None,
            date_source="LOT" if lot is not None else "NONE",
            manufactured_on=lot.dates.manufactured_on if lot is not None else None,
            expires_on=lot.dates.expires_on if lot is not None else None,
        )
