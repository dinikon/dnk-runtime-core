from uuid import UUID

from src.modules.catalog.application.catalog_item.query.find_used_image_files.handler import (
    FindUsedImageFilesHandler as CatalogImages,
)
from src.modules.catalog.application.catalog_item.query.find_used_image_files.query import (
    FindUsedImageFilesQuery as CatalogQuery,
)
from src.modules.channels.application.content_media.query.find_used_image_files.handler import (
    FindUsedImageFilesHandler as ChannelImages,
)
from src.modules.channels.application.content_media.query.find_used_image_files.query import (
    FindUsedImageFilesQuery as ChannelQuery,
)


class ConsumerFileUsage:
    """Вызывает публичные запросы владельцев ссылок, не читая их SQL-модели."""

    def __init__(self, *, catalog: CatalogImages, channels: ChannelImages) -> None:
        """Принимает read-сценарии, собранные на общей сессии внешнего UoW."""
        self._catalog, self._channels = catalog, channels

    async def used(
        self, tenant_id: UUID, file_ids: tuple[UUID, ...]
    ) -> tuple[UUID, ...]:
        """Возвращает объединение ссылок без захвата locks Catalog или Channels."""
        if not file_ids:
            return ()
        catalog = await self._catalog.execute(CatalogQuery(tenant_id, file_ids))
        channels = await self._channels.execute(ChannelQuery(tenant_id, file_ids))
        return tuple(sorted(set(catalog.file_ids) | set(channels.file_ids)))
