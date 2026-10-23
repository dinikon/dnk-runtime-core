from src.modules.catalog.application.catalog_item.query.find_used_image_files.query import (
    FindUsedImageFilesQuery,
)
from src.modules.catalog.application.catalog_item.query.find_used_image_files.dto import (
    FindUsedImageFilesResultDTO,
)
from src.modules.catalog.application.catalog_item.port.image_usage import (
    CatalogImageUsagePort,
)


class FindUsedImageFilesHandler:
    """Предоставляет безопасный публичный запрос использования файлов."""

    def __init__(self, images: CatalogImageUsagePort) -> None:
        """Получает порт Catalog, не чужие ORM или storage."""
        self.images = images

    async def execute(
        self, query: FindUsedImageFilesQuery
    ) -> FindUsedImageFilesResultDTO:
        """Читает проекцию в транзакции потребителя."""
        return await self.images.used_images(query)
