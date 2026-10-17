from typing import Annotated

from fastapi import Depends

from src.modules.reference_data.application.currency.query.get_currency_validation_catalog.handler import (
    GetCurrencyValidationCatalogHandler,
)
from src.modules.reference_data.infrastructure.currency.persistence.validation_catalog_repository import (
    SqlAlchemyCurrencyValidationCatalogQueryRepository,
)
from src.modules.reference_data.application.currency.query.validate_currency.handler import (
    ValidateCurrencyHandler,
)
from src.modules.reference_data.infrastructure.currency.persistence.query_repository import (
    SqlAlchemyCurrencyQueryRepository,
)

from src.modules.reference_data.application.port.catalog import CatalogRepositoryPort
from src.modules.reference_data.infrastructure.persistence.repository import (
    SqlAlchemyCatalogRepository,
)
from src.modules.shared.presentation.persistence.depends import UoWDep
from src.modules.reference_data.application.time_zone.query.check_time_zone.handler import (
    CheckTimeZoneHandler,
)


def get_catalog_repository(uow: UoWDep) -> CatalogRepositoryPort:
    """Собирает существующий порт справочников на сессии общего UoW."""
    return SqlAlchemyCatalogRepository(uow.session)


def get_validate_currency_handler(uow: UoWDep) -> ValidateCurrencyHandler:
    """Собирает публичную проверку валюты без чтения всего справочника."""
    return ValidateCurrencyHandler(SqlAlchemyCurrencyQueryRepository(uow.session))


ValidateCurrencyHandlerDep = Annotated[
    ValidateCurrencyHandler, Depends(get_validate_currency_handler)
]


CatalogRepositoryDep = Annotated[CatalogRepositoryPort, Depends(get_catalog_repository)]


def get_check_time_zone_handler(
    repository: CatalogRepositoryDep,
) -> CheckTimeZoneHandler:
    """Собирает публичную проверку timezone на сессии общего UoW."""
    return CheckTimeZoneHandler(repository)


CheckTimeZoneHandlerDep = Annotated[
    CheckTimeZoneHandler, Depends(get_check_time_zone_handler)
]


def get_currency_validation_catalog_handler(
    uow: UoWDep,
) -> GetCurrencyValidationCatalogHandler:
    """Собирает batch-проверку кодов на сессии общего UoW."""
    return GetCurrencyValidationCatalogHandler(
        SqlAlchemyCurrencyValidationCatalogQueryRepository(uow.session)
    )


GetCurrencyValidationCatalogHandlerDep = Annotated[
    GetCurrencyValidationCatalogHandler,
    Depends(get_currency_validation_catalog_handler),
]
