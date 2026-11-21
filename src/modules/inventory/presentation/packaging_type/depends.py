from typing import Annotated

from fastapi import Depends

from src.modules.shared.presentation.persistence.depends import UoWDep
from src.modules.shared.presentation.uuid.depends import UuidDep
from src.modules.inventory.domain.packaging_type.repository import (
    PackagingTypeRepositoryProtocol,
)
from src.modules.inventory.application.packaging_type.port.query_repository import (
    PackagingTypeQueryRepositoryProtocol,
)
from src.modules.inventory.application.packaging_type.command.create_packaging_type.handler import (
    CreatePackagingTypeHandler,
)
from src.modules.inventory.application.packaging_type.command.delete_packaging_type.handler import (
    DeletePackagingTypeHandler,
)
from src.modules.inventory.application.packaging_type.command.update_packaging_type.handler import (
    UpdatePackagingTypeHandler,
)
from src.modules.inventory.application.packaging_type.query.get_packaging_type.handler import (
    GetPackagingTypeHandler,
)
from src.modules.inventory.application.packaging_type.query.list_packaging_types.handler import (
    ListPackagingTypesHandler,
)
from src.modules.inventory.infrastructure.packaging_type.persistence.repository import (
    SqlAlchemyPackagingTypeRepository,
)
from src.modules.inventory.infrastructure.packaging_type.persistence.query_repository import (
    SqlAlchemyPackagingTypeQueryRepository,
)

from src.modules.inventory.application.packaging_type.port.usage import (
    PackagingTypeUsagePort,
)
from src.modules.inventory.infrastructure.packaging_type.persistence.usage import (
    SqlAlchemyPackagingTypeUsage,
)


def get_packaging_type_repository(uow: UoWDep) -> PackagingTypeRepositoryProtocol:
    """Собирает write-порт на сессии общего внешнего tenant-UoW."""
    return SqlAlchemyPackagingTypeRepository(uow.session)


PackagingTypeRepositoryDep = Annotated[
    PackagingTypeRepositoryProtocol, Depends(get_packaging_type_repository)
]


def get_update_packaging_type_handler(
    repository: PackagingTypeRepositoryDep,
) -> UpdatePackagingTypeHandler:
    """Собирает редактирование на write-порте общего внешнего UoW."""
    return UpdatePackagingTypeHandler(repository)


UpdatePackagingTypeHandlerDep = Annotated[
    UpdatePackagingTypeHandler, Depends(get_update_packaging_type_handler)
]


def get_packaging_type_query_repository(
    uow: UoWDep,
) -> PackagingTypeQueryRepositoryProtocol:
    """Собирает read-порт на той же общей зависимости UoW."""
    return SqlAlchemyPackagingTypeQueryRepository(uow.session)


PackagingTypeQueryRepositoryDep = Annotated[
    PackagingTypeQueryRepositoryProtocol, Depends(get_packaging_type_query_repository)
]


def get_create_packaging_type_handler(
    repository: PackagingTypeRepositoryDep, uuid_generator: UuidDep
) -> CreatePackagingTypeHandler:
    """Собирает создание из write-порта и общего генератора UUID."""
    return CreatePackagingTypeHandler(repository, uuid_generator)


CreatePackagingTypeHandlerDep = Annotated[
    CreatePackagingTypeHandler, Depends(get_create_packaging_type_handler)
]


def get_get_packaging_type_handler(
    repository: PackagingTypeQueryRepositoryDep,
) -> GetPackagingTypeHandler:
    """Собирает сценарий чтения одной карточки."""
    return GetPackagingTypeHandler(repository)


GetPackagingTypeHandlerDep = Annotated[
    GetPackagingTypeHandler, Depends(get_get_packaging_type_handler)
]


def get_list_packaging_types_handler(
    repository: PackagingTypeQueryRepositoryDep,
) -> ListPackagingTypesHandler:
    """Собирает чтение страницы справочника."""
    return ListPackagingTypesHandler(repository)


ListPackagingTypesHandlerDep = Annotated[
    ListPackagingTypesHandler, Depends(get_list_packaging_types_handler)
]


def get_packaging_type_usage(uow: UoWDep) -> PackagingTypeUsagePort:
    """Собирает чтение использования на той же сессии внешнего tenant-UoW."""
    return SqlAlchemyPackagingTypeUsage(uow.session)


PackagingTypeUsageDep = Annotated[
    PackagingTypeUsagePort, Depends(get_packaging_type_usage)
]


def get_delete_packaging_type_handler(
    repository: PackagingTypeRepositoryDep, usage: PackagingTypeUsageDep
) -> DeletePackagingTypeHandler:
    """Собирает удаление и проверку ссылок из портов одной общей транзакции."""
    return DeletePackagingTypeHandler(repository, usage)


DeletePackagingTypeHandlerDep = Annotated[
    DeletePackagingTypeHandler, Depends(get_delete_packaging_type_handler)
]
