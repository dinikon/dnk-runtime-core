from typing import Annotated

from fastapi import Depends

from src.modules.reference_data.application.port.catalog import CatalogRepositoryPort
from src.modules.reference_data.infrastructure.persistence.repository import (
    SqlAlchemyCatalogRepository,
)
from src.modules.shared.presentation.persistence.depends import UoWDep
from src.modules.reference_data.application.time_zone.query.check_time_zone.handler import (
    CheckTimeZoneHandler,
)


def get_catalog_repository(uow: UoWDep) -> CatalogRepositoryPort:
    return SqlAlchemyCatalogRepository(uow.session)


CatalogRepositoryDep = Annotated[CatalogRepositoryPort, Depends(get_catalog_repository)]


def get_check_time_zone_handler(
    repository: CatalogRepositoryDep,
) -> CheckTimeZoneHandler:
    """Собирает публичную проверку timezone на сессии общего UoW."""
    return CheckTimeZoneHandler(repository)


CheckTimeZoneHandlerDep = Annotated[
    CheckTimeZoneHandler, Depends(get_check_time_zone_handler)
]
