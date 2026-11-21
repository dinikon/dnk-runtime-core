from uuid import UUID

from src.modules.catalog.application.catalog_item.query.find_used_image_files.handler import (
    FindUsedImageFilesHandler as CatalogImages,
)
from src.modules.catalog.application.catalog_item.query.find_used_image_files.query import (
    FindUsedImageFilesQuery as CatalogQuery,
)


class ConsumerFileUsage:
    """Вызывает публичные запросы владельцев ссылок, не читая их SQL-модели."""

    def __init__(self, *, catalog: CatalogImages) -> None:
        """Принимает read-сценарии, собранные на общей сессии внешнего UoW."""
        self._catalog = catalog

    async def used(
        self, tenant_id: UUID, file_ids: tuple[UUID, ...]
    ) -> tuple[UUID, ...]:
        """Возвращает используемые файлы без захвата блокировок Catalog."""
        if not file_ids:
            return ()
        catalog = await self._catalog.execute(CatalogQuery(tenant_id, file_ids))
        return catalog.file_ids
