from typing import Annotated

from fastapi import Depends

from src.modules.reference_data.application.port.catalog import CatalogRepositoryPort
from src.modules.reference_data.infrastructure.persistence.repository import (
    SqlAlchemyCatalogRepository,
)
from src.modules.shared.presentation.persistence.depends import UoWDep


def get_catalog_repository(uow: UoWDep) -> CatalogRepositoryPort:
    return SqlAlchemyCatalogRepository(uow.session)


CatalogRepositoryDep = Annotated[CatalogRepositoryPort, Depends(get_catalog_repository)]
