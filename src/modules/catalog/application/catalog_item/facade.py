from typing import Protocol
from uuid import UUID
from src.modules.catalog.application.catalog_item.creation_values import (
    CreateCatalogItemValues,
)
from src.modules.catalog.application.catalog_item.command.create_catalog_item.dto import (
    CreateCatalogItemResultDTO,
)
from src.modules.catalog.application.catalog_item.query.validate_catalog_draft.dto import (
    ValidateCatalogDraftResultDTO,
)
from src.modules.catalog.application.catalog_item.query.list_catalog_items.dto import (
    ListCatalogItemsResultDTO,
)
from src.modules.catalog.application.catalog_item.command.lock_catalog_item_for_binding.dto import (
    LockCatalogItemForBindingResultDTO,
)
from src.modules.catalog.application.catalog_item.query.get_catalog_items_publication_snapshot.dto import (
    GetCatalogItemsPublicationSnapshotResultDTO,
)


class CatalogItemsFacadeProtocol(Protocol):
    """Публичная граница потребителя: создание, проверка, поиск и item-lock."""

    async def create_item(
        self, tenant_id: UUID, actor_id: UUID, values: CreateCatalogItemValues
    ) -> CreateCatalogItemResultDTO:
        """Создаёт Draft внутри внешнего UoW без самостоятельного commit."""
        ...

    async def validate_draft(
        self, tenant_id: UUID, actor_id: UUID, values: CreateCatalogItemValues
    ) -> ValidateCatalogDraftResultDTO:
        """Проверяет значения, не записывая товар."""
        ...

    async def candidates(
        self, tenant_id: UUID, locale: str, search: str | None, offset: int, limit: int
    ) -> ListCatalogItemsResultDTO:
        """Читает страницу самостоятельных товаров."""
        ...

    async def lock_item(
        self, tenant_id: UUID, item_id: UUID
    ) -> LockCatalogItemForBindingResultDTO:
        """Захватывает блокировку владельца и проверяет существование товара."""
        ...

    async def publication_snapshot(
        self, tenant_id: UUID, item_ids: tuple[UUID, ...], locale: str
    ) -> GetCatalogItemsPublicationSnapshotResultDTO:
        """Читает существующую публичную проекцию для публикации без fallback локали."""
        ...
