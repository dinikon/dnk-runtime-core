from uuid import UUID
from src.modules.catalog.application.catalog_item.facade import (
    CatalogItemsFacadeProtocol,
)
from src.modules.catalog.application.catalog_item.creation_values import (
    CreateCatalogItemValues,
)
from src.modules.catalog.application.catalog_item.command.create_catalog_item.command import (
    CreateCatalogItemCommand,
)
from src.modules.catalog.application.catalog_item.command.create_catalog_item.handler import (
    CreateCatalogItemHandler,
)
from src.modules.catalog.application.catalog_item.command.create_catalog_item.dto import (
    CreateCatalogItemResultDTO,
)
from src.modules.catalog.application.catalog_item.query.validate_catalog_draft.query import (
    ValidateCatalogDraftQuery,
)
from src.modules.catalog.application.catalog_item.query.validate_catalog_draft.handler import (
    ValidateCatalogDraftHandler,
)
from src.modules.catalog.application.catalog_item.query.validate_catalog_draft.dto import (
    ValidateCatalogDraftResultDTO,
)
from src.modules.catalog.application.catalog_item.query.list_catalog_items.query import (
    ListCatalogItemsQuery,
)
from src.modules.catalog.application.catalog_item.query.list_catalog_items.handler import (
    ListCatalogItemsHandler,
)
from src.modules.catalog.application.catalog_item.query.list_catalog_items.dto import (
    ListCatalogItemsResultDTO,
)
from src.modules.catalog.application.catalog_item.command.lock_catalog_item_for_binding.command import (
    LockCatalogItemForBindingCommand,
)
from src.modules.catalog.application.catalog_item.command.lock_catalog_item_for_binding.handler import (
    LockCatalogItemForBindingHandler,
)
from src.modules.catalog.application.catalog_item.command.lock_catalog_item_for_binding.dto import (
    LockCatalogItemForBindingResultDTO,
)
from src.modules.catalog.domain.catalog_item.value_object.identifier import (
    CatalogItemIdVO,
)
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.catalog.application.catalog_item.query.get_catalog_items_publication_snapshot.handler import (
    GetCatalogItemsPublicationSnapshotHandler,
)
from src.modules.catalog.application.catalog_item.query.get_catalog_items_publication_snapshot.query import (
    GetCatalogItemsPublicationSnapshotQuery,
)
from src.modules.catalog.application.catalog_item.query.get_catalog_items_publication_snapshot.dto import (
    GetCatalogItemsPublicationSnapshotResultDTO,
)


class CatalogItemsFacade(CatalogItemsFacadeProtocol):
    """Адаптирует публичные сценарии Catalog к границе потребителя."""

    def __init__(
        self,
        create: CreateCatalogItemHandler,
        validate: ValidateCatalogDraftHandler,
        listing: ListCatalogItemsHandler,
        locking: LockCatalogItemForBindingHandler,
        snapshots: GetCatalogItemsPublicationSnapshotHandler,
    ) -> None:
        """Принимает обработчики, собранные на одном внешнем UoW."""
        self.create, self.validate, self.listing, self.locking = (
            create,
            validate,
            listing,
            locking,
        )
        self.snapshots = snapshots

    async def create_item(
        self, tenant_id: UUID, actor_id: UUID, values: CreateCatalogItemValues
    ) -> CreateCatalogItemResultDTO:
        """Вызывает атомарное создание Catalog без HTTP и commit."""
        return await self.create.execute(
            CreateCatalogItemCommand(
                EntityIdVO(tenant_id), EntityIdVO(actor_id), values
            )
        )

    async def validate_draft(
        self, tenant_id: UUID, actor_id: UUID, values: CreateCatalogItemValues
    ) -> ValidateCatalogDraftResultDTO:
        """Возвращает структурированные ошибки значения preview."""
        return await self.validate.execute(
            ValidateCatalogDraftQuery(
                EntityIdVO(tenant_id), EntityIdVO(actor_id), values
            )
        )

    async def candidates(
        self, tenant_id: UUID, locale: str, search: str | None, offset: int, limit: int
    ) -> ListCatalogItemsResultDTO:
        """Делегирует публичному read-сценарию Catalog."""
        return await self.listing.execute(
            ListCatalogItemsQuery(
                EntityIdVO(tenant_id), locale, search=search, offset=offset, limit=limit
            )
        )

    async def lock_item(
        self, tenant_id: UUID, item_id: UUID
    ) -> LockCatalogItemForBindingResultDTO:
        """Сериализует существующий товар с удалением и другими bindings."""
        return await self.locking.execute(
            LockCatalogItemForBindingCommand(
                EntityIdVO(tenant_id), CatalogItemIdVO(item_id)
            )
        )

    async def publication_snapshot(
        self, tenant_id: UUID, item_ids: tuple[UUID, ...], locale: str
    ) -> GetCatalogItemsPublicationSnapshotResultDTO:
        """Переиспользует согласованный read-сценарий владельца контента."""
        return await self.snapshots.execute(
            GetCatalogItemsPublicationSnapshotQuery(
                EntityIdVO(tenant_id),
                tuple(CatalogItemIdVO(identifier) for identifier in item_ids),
                locale,
            )
        )
