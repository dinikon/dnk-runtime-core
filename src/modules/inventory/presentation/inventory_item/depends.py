from typing import Annotated
from src.modules.inventory.application.inventory_item.query.get_inventory_item.handler import (
    GetInventoryItemHandler,
)
from src.modules.catalog.application.catalog_item.query.find_inventory_item_usage.handler import (
    FindInventoryItemUsageHandler,
)
from src.modules.catalog.infrastructure.catalog_item.sku import SqlAlchemyCatalogItemSku
from src.modules.inventory.infrastructure.inventory_item.catalog_usage import (
    CatalogInventoryItemUsage,
)
from src.modules.inventory.application.inventory_item.command.update_inventory_item.handler import (
    UpdateInventoryItemHandler,
)
from src.modules.inventory.application.inventory_item.command.delete_inventory_item.handler import (
    DeleteInventoryItemHandler,
)

from fastapi import Depends

from src.modules.inventory.application.inventory_item.command.create_inventory_item.handler import (
    CreateInventoryItemHandler,
)
from src.modules.inventory.application.inventory_item.port.query_repository import (
    InventoryItemQueryRepositoryProtocol,
)
from src.modules.inventory.application.inventory_item.query.list_inventory_items.handler import (
    ListInventoryItemsHandler,
)
from src.modules.inventory.domain.inventory_item.repository import (
    InventoryItemRepositoryProtocol,
)
from src.modules.inventory.infrastructure.inventory_item.persistence.query_repository import (
    SqlAlchemyInventoryItemQueryRepository,
)
from src.modules.inventory.infrastructure.inventory_item.persistence.repository import (
    SqlAlchemyInventoryItemRepository,
)
from src.modules.shared.presentation.persistence.depends import UoWDep
from src.modules.shared.presentation.uuid.depends import UuidDep


def get_inventory_item_repository(uow: UoWDep) -> InventoryItemRepositoryProtocol:
    """Подключает write-адаптер к общей сессии внешнего UoW."""
    return SqlAlchemyInventoryItemRepository(uow.session)


InventoryItemRepositoryDep = Annotated[
    InventoryItemRepositoryProtocol, Depends(get_inventory_item_repository)
]


def get_inventory_item_query_repository(
    uow: UoWDep,
) -> InventoryItemQueryRepositoryProtocol:
    """Подключает read-адаптер к сессии с выбранной tenant-схемой."""
    return SqlAlchemyInventoryItemQueryRepository(uow.session)


InventoryItemQueryRepositoryDep = Annotated[
    InventoryItemQueryRepositoryProtocol, Depends(get_inventory_item_query_repository)
]


def get_create_inventory_item_handler(
    repository: InventoryItemRepositoryDep, uuid_generator: UuidDep
) -> CreateInventoryItemHandler:
    """Собирает создание без передачи SQL-сессии или UoW в Application."""
    return CreateInventoryItemHandler(repository, uuid_generator)


CreateInventoryItemHandlerDep = Annotated[
    CreateInventoryItemHandler, Depends(get_create_inventory_item_handler)
]


def get_list_inventory_items_handler(
    repository: InventoryItemQueryRepositoryDep,
) -> ListInventoryItemsHandler:
    """Собирает сценарий списка из порта проекций."""
    return ListInventoryItemsHandler(repository)


ListInventoryItemsHandlerDep = Annotated[
    ListInventoryItemsHandler, Depends(get_list_inventory_items_handler)
]


def get_get_inventory_item_handler(
    repository: InventoryItemQueryRepositoryDep,
) -> GetInventoryItemHandler:
    """Собирает чтение карточки из порта проекций текущего tenant."""
    return GetInventoryItemHandler(repository)


GetInventoryItemHandlerDep = Annotated[
    GetInventoryItemHandler, Depends(get_get_inventory_item_handler)
]


def get_update_inventory_item_handler(
    repository: InventoryItemRepositoryDep, uuid_generator: UuidDep
) -> UpdateInventoryItemHandler:
    """Собирает обновление на write-порте общей сессии."""
    return UpdateInventoryItemHandler(repository, uuid_generator)


UpdateInventoryItemHandlerDep = Annotated[
    UpdateInventoryItemHandler, Depends(get_update_inventory_item_handler)
]


def get_delete_inventory_item_handler(
    repository: InventoryItemRepositoryDep,
    uow: UoWDep,
) -> DeleteInventoryItemHandler:
    """Собирает удаление без передачи транзакции во внутренние слои."""
    return DeleteInventoryItemHandler(
        repository,
        CatalogInventoryItemUsage(
            FindInventoryItemUsageHandler(SqlAlchemyCatalogItemSku(uow.session))
        ),
    )


DeleteInventoryItemHandlerDep = Annotated[
    DeleteInventoryItemHandler, Depends(get_delete_inventory_item_handler)
]
