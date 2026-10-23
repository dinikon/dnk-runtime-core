from typing import Protocol
from datetime import datetime
from src.modules.catalog.application.catalog_item.query.get_catalog_item.query import (
    GetCatalogItemQuery,
)
from src.modules.catalog.application.catalog_item.query.get_catalog_item.dto import (
    GetCatalogItemResultDTO,
)
from src.modules.catalog.application.catalog_item.query.list_catalog_items.query import (
    ListCatalogItemsQuery,
)
from src.modules.catalog.application.catalog_item.query.list_catalog_items.dto import (
    ListCatalogItemsResultDTO,
)


class CatalogItemQueryRepositoryProtocol(Protocol):
    """Порт согласованных проекций, возвращающий DTO конкретных сценариев."""

    async def get(
        self, query: GetCatalogItemQuery, as_of: datetime
    ) -> GetCatalogItemResultDTO:
        """Возвращает результат get_catalog_item без Aggregate объектов."""
        ...

    async def list(
        self, query: ListCatalogItemsQuery, as_of: datetime
    ) -> ListCatalogItemsResultDTO:
        """Возвращает результат list_catalog_items без Aggregate объектов."""
        ...
