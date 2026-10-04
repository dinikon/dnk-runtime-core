from typing import Annotated

from fastapi import Depends

from src.modules.inventory.application.sku.command.create_sku.handler import (
    CreateSkuHandler,
)
from src.modules.inventory.application.sku.port.query_repository import (
    SkuQueryRepositoryProtocol,
)
from src.modules.inventory.application.sku.port.sku_lookup import SkuLookupProtocol
from src.modules.inventory.application.sku.query.get_sku.handler import GetSkuHandler
from src.modules.inventory.application.sku.query.list_skus.handler import (
    ListSkusHandler,
)
from src.modules.inventory.application.sku.service.sku_lookup import SkuLookupService
from src.modules.inventory.domain.sku.repository import SkuRepositoryProtocol
from src.modules.inventory.infrastructure.sku.persistence.repository import (
    SqlAlchemySkuRepository,
)
from src.modules.inventory.infrastructure.sku.persistence.query_repository import (
    SqlAlchemySkuQueryRepository,
)
from src.modules.shared.presentation.persistence.depends import UoWDep
from src.modules.shared.presentation.time.depends import ClockDep
from src.modules.shared.presentation.uuid.depends import UuidDep


def get_sku_repository(uow: UoWDep) -> SkuRepositoryProtocol:
    """Связывает запись с общим UoW запроса."""
    return SqlAlchemySkuRepository(uow.session)


SkuRepositoryDep = Annotated[SkuRepositoryProtocol, Depends(get_sku_repository)]


def get_sku_query_repository(uow: UoWDep) -> SkuQueryRepositoryProtocol:
    """Связывает чтение с тем же tenant connection."""
    return SqlAlchemySkuQueryRepository(uow.session)


SkuQueryRepositoryDep = Annotated[
    SkuQueryRepositoryProtocol, Depends(get_sku_query_repository)
]


def get_create_sku_handler(
    repository: SkuRepositoryDep, clock: ClockDep, uuid_generator: UuidDep
) -> CreateSkuHandler:
    """Собирает сценарий создания без бизнес-правил в DI."""
    return CreateSkuHandler(repository, clock, uuid_generator)


CreateSkuHandlerDep = Annotated[CreateSkuHandler, Depends(get_create_sku_handler)]


def get_get_sku_handler(repository: SkuQueryRepositoryDep) -> GetSkuHandler:
    """Собирает чтение учётной позиции."""
    return GetSkuHandler(repository)


GetSkuHandlerDep = Annotated[GetSkuHandler, Depends(get_get_sku_handler)]


def get_list_skus_handler(repository: SkuQueryRepositoryDep) -> ListSkusHandler:
    """Собирает чтение страницы SKU."""
    return ListSkusHandler(repository)


ListSkusHandlerDep = Annotated[ListSkusHandler, Depends(get_list_skus_handler)]


def get_sku_lookup(repository: SkuQueryRepositoryDep) -> SkuLookupProtocol:
    """Предоставляет будущему Catalog публичный порт текущего tenant."""
    return SkuLookupService(repository)


SkuLookupDep = Annotated[SkuLookupProtocol, Depends(get_sku_lookup)]
