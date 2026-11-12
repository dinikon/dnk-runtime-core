from typing import Annotated

from fastapi import Depends

from src.modules.shared.presentation.persistence.depends import UoWDep
from src.modules.shared.presentation.uuid.depends import UuidDep
from src.modules.inventory.domain.warehouse.repository import (
    WarehouseRepositoryProtocol,
)
from src.modules.inventory.domain.stock_location.repository import (
    StockLocationRepositoryProtocol,
)
from src.modules.inventory.application.warehouse.port.query_repository import (
    WarehouseQueryRepositoryProtocol,
)
from src.modules.inventory.application.warehouse.command.create_warehouse.handler import (
    CreateWarehouseHandler,
)
from src.modules.inventory.application.warehouse.query.get_warehouse.handler import (
    GetWarehouseHandler,
)
from src.modules.inventory.application.warehouse.query.list_warehouses.handler import (
    ListWarehousesHandler,
)
from src.modules.inventory.infrastructure.warehouse.persistence.repository import (
    SqlAlchemyWarehouseRepository,
)
from src.modules.inventory.infrastructure.stock_location.persistence.repository import (
    SqlAlchemyStockLocationRepository,
)
from src.modules.inventory.infrastructure.warehouse.persistence.query_repository import (
    SqlAlchemyWarehouseQueryRepository,
)


def get_warehouse_repository(uow: UoWDep) -> WarehouseRepositoryProtocol:
    """Собирает write-порт склада на сессии общего UoW."""
    return SqlAlchemyWarehouseRepository(uow.session)


WarehouseRepositoryDep = Annotated[
    WarehouseRepositoryProtocol, Depends(get_warehouse_repository)
]


def get_stock_location_repository(uow: UoWDep) -> StockLocationRepositoryProtocol:
    """Собирает write-порт локаций на той же сессии UoW."""
    return SqlAlchemyStockLocationRepository(uow.session)


StockLocationRepositoryDep = Annotated[
    StockLocationRepositoryProtocol, Depends(get_stock_location_repository)
]


def get_warehouse_query_repository(uow: UoWDep) -> WarehouseQueryRepositoryProtocol:
    """Собирает read-порт на сессии текущего tenant."""
    return SqlAlchemyWarehouseQueryRepository(uow.session)


WarehouseQueryRepositoryDep = Annotated[
    WarehouseQueryRepositoryProtocol, Depends(get_warehouse_query_repository)
]


def get_create_warehouse_handler(
    warehouses: WarehouseRepositoryDep,
    locations: StockLocationRepositoryDep,
    uuid_generator: UuidDep,
) -> CreateWarehouseHandler:
    """Собирает координацию двух агрегатов без передачи сессии в Application."""
    return CreateWarehouseHandler(warehouses, locations, uuid_generator)


CreateWarehouseHandlerDep = Annotated[
    CreateWarehouseHandler, Depends(get_create_warehouse_handler)
]


def get_get_warehouse_handler(
    repository: WarehouseQueryRepositoryDep,
) -> GetWarehouseHandler:
    """Собирает сценарий карточки склада."""
    return GetWarehouseHandler(repository)


GetWarehouseHandlerDep = Annotated[
    GetWarehouseHandler, Depends(get_get_warehouse_handler)
]


def get_list_warehouses_handler(
    repository: WarehouseQueryRepositoryDep,
) -> ListWarehousesHandler:
    """Собирает сценарий списка складов."""
    return ListWarehousesHandler(repository)


ListWarehousesHandlerDep = Annotated[
    ListWarehousesHandler, Depends(get_list_warehouses_handler)
]
