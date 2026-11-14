from typing import Annotated
from fastapi import Depends

from src.modules.inventory.presentation.stock_lot.depends import StockLotRepositoryDep
from src.modules.inventory.application.stock_serial.command.create_stock_serial.handler import (
    CreateStockSerialHandler,
)
from src.modules.inventory.application.stock_serial.port.query_repository import (
    StockSerialQueryRepositoryProtocol,
)
from src.modules.inventory.application.stock_serial.query.get_stock_serial.handler import (
    GetStockSerialHandler,
)
from src.modules.inventory.application.stock_serial.query.list_stock_serials.handler import (
    ListStockSerialsHandler,
)
from src.modules.inventory.domain.stock_serial.repository import (
    StockSerialRepositoryProtocol,
)
from src.modules.inventory.infrastructure.stock_serial.persistence.query_repository import (
    SqlAlchemyStockSerialQueryRepository,
)
from src.modules.inventory.infrastructure.stock_serial.persistence.repository import (
    SqlAlchemyStockSerialRepository,
)
from src.modules.inventory.presentation.inventory_item.depends import (
    InventoryItemRepositoryDep,
)
from src.modules.shared.presentation.persistence.depends import UoWDep
from src.modules.shared.presentation.uuid.depends import UuidDep


def get_stock_serial_repository(uow: UoWDep) -> StockSerialRepositoryProtocol:
    """Собирает write-порт экземпляра на сессии общего внешнего UoW."""
    return SqlAlchemyStockSerialRepository(uow.session)


StockSerialRepositoryDep = Annotated[
    StockSerialRepositoryProtocol, Depends(get_stock_serial_repository)
]


def get_stock_serial_query_repository(
    uow: UoWDep,
) -> StockSerialQueryRepositoryProtocol:
    """Собирает read-порт на той же общей зависимости tenant-UoW."""
    return SqlAlchemyStockSerialQueryRepository(uow.session)


StockSerialQueryRepositoryDep = Annotated[
    StockSerialQueryRepositoryProtocol, Depends(get_stock_serial_query_repository)
]


def get_create_stock_serial_handler(
    items: InventoryItemRepositoryDep,
    lots: StockLotRepositoryDep,
    serials: StockSerialRepositoryDep,
    uuid_generator: UuidDep,
) -> CreateStockSerialHandler:
    """Подключает три write-порта к одной транзакции без передачи UoW в handler."""
    return CreateStockSerialHandler(items, lots, serials, uuid_generator)


CreateStockSerialHandlerDep = Annotated[
    CreateStockSerialHandler, Depends(get_create_stock_serial_handler)
]


def get_get_stock_serial_handler(
    repository: StockSerialQueryRepositoryDep,
) -> GetStockSerialHandler:
    """Собирает чтение карточки через порт проекций."""
    return GetStockSerialHandler(repository)


GetStockSerialHandlerDep = Annotated[
    GetStockSerialHandler, Depends(get_get_stock_serial_handler)
]


def get_list_stock_serials_handler(
    repository: StockSerialQueryRepositoryDep,
) -> ListStockSerialsHandler:
    """Собирает чтение списка через порт проекций."""
    return ListStockSerialsHandler(repository)


ListStockSerialsHandlerDep = Annotated[
    ListStockSerialsHandler, Depends(get_list_stock_serials_handler)
]
