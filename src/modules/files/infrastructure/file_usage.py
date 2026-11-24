from uuid import UUID
from src.modules.feed_builder.application.export_state.query.find_used_feed_export_files.handler import (
    FindUsedFeedExportFilesHandler,
)
from src.modules.feed_builder.application.export_state.query.find_used_feed_export_files.query import (
    FindUsedFeedExportFilesQuery,
)

from src.modules.catalog.application.catalog_item.query.find_used_image_files.handler import (
    FindUsedImageFilesHandler as CatalogImages,
)
from src.modules.catalog.application.catalog_item.query.find_used_image_files.query import (
    FindUsedImageFilesQuery as CatalogQuery,
)


class ConsumerFileUsage:
    """Вызывает публичные запросы владельцев ссылок, не читая их SQL-модели."""

    def __init__(
        self, *, catalog: CatalogImages, exports: FindUsedFeedExportFilesHandler
    ) -> None:
        """Принимает read-сценарии, собранные на общей сессии внешнего UoW."""
        self._catalog = catalog
        self._exports = exports

    async def used(
        self, tenant_id: UUID, file_ids: tuple[UUID, ...]
    ) -> tuple[UUID, ...]:
        """Возвращает используемые файлы без захвата блокировок Catalog."""
        if not file_ids:
            return ()
        catalog = await self._catalog.execute(CatalogQuery(tenant_id, file_ids))
        export_ids = await self._exports.execute(FindUsedFeedExportFilesQuery(file_ids))
        used = set(catalog.file_ids).union(export_ids)
        return tuple(dict.fromkeys(file_id for file_id in file_ids if file_id in used))
