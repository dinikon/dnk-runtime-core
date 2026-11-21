from uuid import UUID
from src.modules.catalog.application.catalog_item.query.get_catalog_variant.query import (
    GetCatalogVariantQuery,
)
from src.modules.catalog.application.catalog_item.query.get_catalog_variant.dto import (
    GetCatalogVariantResultDTO,
)
from src.modules.catalog.application.catalog_item.query.list_catalog_variants.query import (
    ListCatalogVariantsQuery,
)
from src.modules.catalog.application.catalog_item.query.list_catalog_variants.dto import (
    ListCatalogVariantsResultDTO,
)
from src.modules.catalog.application.catalog_item.query.get_catalog_product_snapshot.query import (
    GetCatalogProductSnapshotQuery,
)
from src.modules.catalog.application.catalog_item.query.get_catalog_product_snapshot.dto import (
    GetCatalogProductSnapshotResultDTO,
)
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

    async def get_variant(
        self, query: GetCatalogVariantQuery, as_of: datetime
    ) -> GetCatalogVariantResultDTO:
        """Читает конкретную проекцию семьи на согласованный момент."""
        ...

    async def list_variants(
        self, query: ListCatalogVariantsQuery, as_of: datetime
    ) -> ListCatalogVariantsResultDTO:
        """Читает конкретную проекцию семьи на согласованный момент."""
        ...

    async def get_snapshot(
        self, query: GetCatalogProductSnapshotQuery, as_of: datetime
    ) -> GetCatalogProductSnapshotResultDTO:
        """Читает конкретную проекцию семьи на согласованный момент."""
        ...

    async def snapshots(
        self, identifiers: tuple[UUID, ...], locale: str, as_of: datetime
    ) -> tuple[GetCatalogProductSnapshotResultDTO, ...]:
        """Передаёт пакетные публичные снимки без восстановления агрегатов."""
        ...
