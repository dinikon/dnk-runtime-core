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

from src.modules.inventory.application.inventory_item.command.delete_item_packaging.handler import (
    DeleteItemPackagingHandler,
)
from src.modules.inventory.application.inventory_item.command.update_item_packaging.handler import (
    UpdateItemPackagingHandler,
)
from src.modules.inventory.application.inventory_item.command.add_item_packaging.handler import (
    AddItemPackagingHandler,
)
from src.modules.inventory.application.inventory_item.query.get_item_packaging.handler import (
    GetItemPackagingHandler,
)
from src.modules.inventory.application.inventory_item.query.list_item_packagings.handler import (
    ListItemPackagingsHandler,
)
from src.modules.inventory.application.inventory_item.port.item_packaging_query_repository import (
    ItemPackagingQueryRepositoryProtocol,
)
from src.modules.inventory.infrastructure.inventory_item.persistence.item_packaging_query_repository import (
    SqlAlchemyItemPackagingQueryRepository,
)
from src.modules.inventory.presentation.packaging_type.depends import (
    PackagingTypeRepositoryDep,
)
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


def get_item_packaging_query_repository(
    uow: UoWDep,
) -> ItemPackagingQueryRepositoryProtocol:
    """Собирает чтение упаковок на общей сессии внешнего tenant-UoW."""
    return SqlAlchemyItemPackagingQueryRepository(uow.session)


ItemPackagingQueryRepositoryDep = Annotated[
    ItemPackagingQueryRepositoryProtocol, Depends(get_item_packaging_query_repository)
]


def get_add_item_packaging_handler(
    items: InventoryItemRepositoryDep,
    types: PackagingTypeRepositoryDep,
    uuid_generator: UuidDep,
) -> AddItemPackagingHandler:
    """Подключает оба write-порта к одной зависимости общего UoW."""
    return AddItemPackagingHandler(items, types, uuid_generator)


AddItemPackagingHandlerDep = Annotated[
    AddItemPackagingHandler, Depends(get_add_item_packaging_handler)
]


def get_get_item_packaging_handler(
    repository: ItemPackagingQueryRepositoryDep,
) -> GetItemPackagingHandler:
    """Собирает сценарий карточки упаковки из read-порта."""
    return GetItemPackagingHandler(repository)


GetItemPackagingHandlerDep = Annotated[
    GetItemPackagingHandler, Depends(get_get_item_packaging_handler)
]


def get_list_item_packagings_handler(
    repository: ItemPackagingQueryRepositoryDep,
) -> ListItemPackagingsHandler:
    """Собирает сценарий списка упаковок из read-порта."""
    return ListItemPackagingsHandler(repository)


ListItemPackagingsHandlerDep = Annotated[
    ListItemPackagingsHandler, Depends(get_list_item_packagings_handler)
]


def get_update_item_packaging_handler(
    items: InventoryItemRepositoryDep, types: PackagingTypeRepositoryDep
) -> UpdateItemPackagingHandler:
    """Собирает изменение упаковки на двух write-портах общего внешнего UoW."""
    return UpdateItemPackagingHandler(items, types)


UpdateItemPackagingHandlerDep = Annotated[
    UpdateItemPackagingHandler, Depends(get_update_item_packaging_handler)
]


def get_delete_item_packaging_handler(
    repository: InventoryItemRepositoryDep,
) -> DeleteItemPackagingHandler:
    """Собирает удаление дочерней Entity на write-порте общего tenant-UoW."""
    return DeleteItemPackagingHandler(repository)


DeleteItemPackagingHandlerDep = Annotated[
    DeleteItemPackagingHandler, Depends(get_delete_item_packaging_handler)
]
