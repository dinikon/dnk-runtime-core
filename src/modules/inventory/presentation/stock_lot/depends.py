from typing import Annotated

from fastapi import Depends

from src.modules.inventory.application.stock_lot.command.create_stock_lot.handler import (
    CreateStockLotHandler,
)
from src.modules.inventory.application.stock_lot.command.update_stock_lot.handler import (
    UpdateStockLotHandler,
)
from src.modules.inventory.application.stock_lot.port.query_repository import (
    StockLotQueryRepositoryProtocol,
)
from src.modules.inventory.application.stock_lot.query.get_stock_lot.handler import (
    GetStockLotHandler,
)
from src.modules.inventory.application.stock_lot.query.list_stock_lots.handler import (
    ListStockLotsHandler,
)
from src.modules.inventory.domain.stock_lot.repository import StockLotRepositoryProtocol
from src.modules.inventory.infrastructure.stock_lot.persistence.query_repository import (
    SqlAlchemyStockLotQueryRepository,
)
from src.modules.inventory.infrastructure.stock_lot.persistence.repository import (
    SqlAlchemyStockLotRepository,
)
from src.modules.inventory.presentation.inventory_item.depends import (
    InventoryItemRepositoryDep,
)
from src.modules.shared.presentation.persistence.depends import UoWDep
from src.modules.shared.presentation.uuid.depends import UuidDep


def get_stock_lot_repository(uow: UoWDep) -> StockLotRepositoryProtocol:
    """Собирает write-порт партии на сессии общего внешнего UoW."""
    return SqlAlchemyStockLotRepository(uow.session)


StockLotRepositoryDep = Annotated[
    StockLotRepositoryProtocol, Depends(get_stock_lot_repository)
]


def get_stock_lot_query_repository(uow: UoWDep) -> StockLotQueryRepositoryProtocol:
    """Собирает read-порт на той же общей зависимости tenant-UoW."""
    return SqlAlchemyStockLotQueryRepository(uow.session)


StockLotQueryRepositoryDep = Annotated[
    StockLotQueryRepositoryProtocol, Depends(get_stock_lot_query_repository)
]


def get_create_stock_lot_handler(
    items: InventoryItemRepositoryDep,
    lots: StockLotRepositoryDep,
    uuid_generator: UuidDep,
) -> CreateStockLotHandler:
    """Подключает оба write-порта к одной транзакции без передачи UoW в handler."""
    return CreateStockLotHandler(items, lots, uuid_generator)


CreateStockLotHandlerDep = Annotated[
    CreateStockLotHandler, Depends(get_create_stock_lot_handler)
]


def get_get_stock_lot_handler(
    repository: StockLotQueryRepositoryDep,
) -> GetStockLotHandler:
    """Собирает чтение карточки через порт проекций."""
    return GetStockLotHandler(repository)


GetStockLotHandlerDep = Annotated[
    GetStockLotHandler, Depends(get_get_stock_lot_handler)
]


def get_list_stock_lots_handler(
    repository: StockLotQueryRepositoryDep,
) -> ListStockLotsHandler:
    """Собирает чтение списка через порт проекций."""
    return ListStockLotsHandler(repository)


ListStockLotsHandlerDep = Annotated[
    ListStockLotsHandler, Depends(get_list_stock_lots_handler)
]


def get_update_stock_lot_handler(
    items: InventoryItemRepositoryDep, lots: StockLotRepositoryDep
) -> UpdateStockLotHandler:
    """Подключает обновление к write-портам одной общей tenant-транзакции."""
    return UpdateStockLotHandler(items, lots)


UpdateStockLotHandlerDep = Annotated[
    UpdateStockLotHandler, Depends(get_update_stock_lot_handler)
]
