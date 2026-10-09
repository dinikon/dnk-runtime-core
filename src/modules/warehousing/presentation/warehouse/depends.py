from typing import Annotated

from fastapi import Depends

from src.modules.reference_data.presentation.depends import CheckTimeZoneHandlerDep
from src.modules.shared.presentation.persistence.depends import UoWDep
from src.modules.shared.presentation.time.depends import ClockDep
from src.modules.shared.presentation.uuid.depends import UuidDep
from src.modules.warehousing.application.port.time_zone_reader import (
    TimeZoneReaderProtocol,
)
from src.modules.warehousing.application.warehouse.command.create_warehouse.handler import (
    CreateWarehouseHandler,
)
from src.modules.warehousing.application.warehouse.port.query_repository import (
    WarehouseQueryRepositoryProtocol,
)
from src.modules.warehousing.application.warehouse.query.get_warehouse.handler import (
    GetWarehouseHandler,
)
from src.modules.warehousing.application.warehouse.query.list_warehouses.handler import (
    ListWarehousesHandler,
)
from src.modules.warehousing.domain.warehouse.repository import (
    WarehouseRepositoryProtocol,
)
from src.modules.warehousing.infrastructure.adapter.time_zone_reader import (
    ReferenceDataTimeZoneReader,
)
from src.modules.warehousing.infrastructure.warehouse.persistence.query_repository import (
    SqlAlchemyWarehouseQueryRepository,
)
from src.modules.warehousing.infrastructure.warehouse.persistence.repository import (
    SqlAlchemyWarehouseRepository,
)


def get_warehouse_repository(uow: UoWDep) -> WarehouseRepositoryProtocol:
    """Собирает write repository на общей tenant-session."""
    return SqlAlchemyWarehouseRepository(uow.session)


WarehouseRepositoryDep = Annotated[
    WarehouseRepositoryProtocol, Depends(get_warehouse_repository)
]


def get_warehouse_query_repository(uow: UoWDep) -> WarehouseQueryRepositoryProtocol:
    """Собирает read repository на той же внешней session."""
    return SqlAlchemyWarehouseQueryRepository(uow.session)


WarehouseQueryRepositoryDep = Annotated[
    WarehouseQueryRepositoryProtocol, Depends(get_warehouse_query_repository)
]


def get_time_zone_reader(handler: CheckTimeZoneHandlerDep) -> TimeZoneReaderProtocol:
    """Подключает публичный reader справочника через собственный адаптер."""
    return ReferenceDataTimeZoneReader(handler)


TimeZoneReaderDep = Annotated[TimeZoneReaderProtocol, Depends(get_time_zone_reader)]


def get_create_warehouse_handler(
    repository: WarehouseRepositoryDep,
    time_zones: TimeZoneReaderDep,
    clock: ClockDep,
    uuid_generator: UuidDep,
) -> CreateWarehouseHandler:
    """Собирает создание склада без передачи session или UoW в Application."""
    return CreateWarehouseHandler(
        repository=repository,
        time_zones=time_zones,
        clock=clock,
        uuid_generator=uuid_generator,
    )


CreateWarehouseHandlerDep = Annotated[
    CreateWarehouseHandler, Depends(get_create_warehouse_handler)
]


def get_get_warehouse_handler(
    repository: WarehouseQueryRepositoryDep,
) -> GetWarehouseHandler:
    """Собирает чтение карточки через порт проекций."""
    return GetWarehouseHandler(repository)


GetWarehouseHandlerDep = Annotated[
    GetWarehouseHandler, Depends(get_get_warehouse_handler)
]


def get_list_warehouses_handler(
    repository: WarehouseQueryRepositoryDep,
) -> ListWarehousesHandler:
    """Собирает чтение списка через порт проекций."""
    return ListWarehousesHandler(repository)


ListWarehousesHandlerDep = Annotated[
    ListWarehousesHandler, Depends(get_list_warehouses_handler)
]
