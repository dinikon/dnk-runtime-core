from typing import Annotated

from fastapi import Depends

from src.modules.inventory.application.stock_location.command.update_stock_location.handler import (
    UpdateStockLocationHandler,
)

from src.modules.inventory.application.stock_location.command.create_stock_location.handler import (
    CreateStockLocationHandler,
)
from src.modules.inventory.application.stock_location.query.get_stock_location.handler import (
    GetStockLocationHandler,
)
from src.modules.inventory.application.stock_location.query.list_stock_locations.handler import (
    ListStockLocationsHandler,
)
from src.modules.inventory.application.stock_location.port.query_repository import (
    StockLocationQueryRepositoryProtocol,
)
from src.modules.inventory.domain.stock_location.repository import (
    StockLocationRepositoryProtocol,
)
from src.modules.inventory.infrastructure.stock_location.persistence.repository import (
    SqlAlchemyStockLocationRepository,
)
from src.modules.inventory.infrastructure.stock_location.persistence.query_repository import (
    SqlAlchemyStockLocationQueryRepository,
)
from src.modules.inventory.presentation.warehouse.depends import WarehouseRepositoryDep
from src.modules.shared.presentation.persistence.depends import UoWDep
from src.modules.shared.presentation.uuid.depends import UuidDep


def get_stock_location_repository(uow: UoWDep) -> StockLocationRepositoryProtocol:
    """Собирает write-порт локаций на сессии общего tenant-UoW."""
    return SqlAlchemyStockLocationRepository(uow.session)


StockLocationRepositoryDep = Annotated[
    StockLocationRepositoryProtocol, Depends(get_stock_location_repository)
]


def get_stock_location_query_repository(
    uow: UoWDep,
) -> StockLocationQueryRepositoryProtocol:
    """Собирает порт проекций без восстановления агрегатов."""
    return SqlAlchemyStockLocationQueryRepository(uow.session)


StockLocationQueryRepositoryDep = Annotated[
    StockLocationQueryRepositoryProtocol, Depends(get_stock_location_query_repository)
]


def get_create_stock_location_handler(
    warehouses: WarehouseRepositoryDep,
    locations: StockLocationRepositoryDep,
    uuid_generator: UuidDep,
) -> CreateStockLocationHandler:
    """Подключает два write-порта одной сессии и генератор ID."""
    return CreateStockLocationHandler(warehouses, locations, uuid_generator)


CreateStockLocationHandlerDep = Annotated[
    CreateStockLocationHandler, Depends(get_create_stock_location_handler)
]


def get_update_stock_location_handler(
    warehouses: WarehouseRepositoryDep,
    locations: StockLocationRepositoryDep,
) -> UpdateStockLocationHandler:
    """Собирает обновление через write-порты одной сессии общего UoW."""
    return UpdateStockLocationHandler(warehouses, locations)


UpdateStockLocationHandlerDep = Annotated[
    UpdateStockLocationHandler, Depends(get_update_stock_location_handler)
]


def get_get_stock_location_handler(
    repository: StockLocationQueryRepositoryDep,
) -> GetStockLocationHandler:
    """Собирает чтение карточки через порт проекций."""
    return GetStockLocationHandler(repository)


GetStockLocationHandlerDep = Annotated[
    GetStockLocationHandler, Depends(get_get_stock_location_handler)
]


def get_list_stock_locations_handler(
    repository: StockLocationQueryRepositoryDep,
) -> ListStockLocationsHandler:
    """Собирает чтение страницы через тот же порт проекций."""
    return ListStockLocationsHandler(repository)


ListStockLocationsHandlerDep = Annotated[
    ListStockLocationsHandler, Depends(get_list_stock_locations_handler)
]
