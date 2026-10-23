from typing import Protocol
from src.modules.catalog.application.catalog_item.query.find_used_image_files.query import (
    FindUsedImageFilesQuery,
)
from src.modules.catalog.application.catalog_item.query.find_used_image_files.dto import (
    FindUsedImageFilesResultDTO,
)


class CatalogImageUsagePort(Protocol):
    """Читает ссылки на файлы без восстановления товарных агрегатов."""

    async def used_images(
        self, query: FindUsedImageFilesQuery
    ) -> FindUsedImageFilesResultDTO:
        """Возвращает только используемые Catalog идентификаторы."""
        ...
