from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.modules.catalog.infrastructure.persistence.models.catalog_item_image import (
    CatalogItemImageModel,
)
from src.modules.catalog.application.catalog_item.query.find_used_image_files.query import (
    FindUsedImageFilesQuery,
)
from src.modules.catalog.application.catalog_item.query.find_used_image_files.dto import (
    FindUsedImageFilesResultDTO,
)


class SqlAlchemyCatalogImageUsage:
    """Читает собственные ссылки Catalog для публичного read-сценария."""

    def __init__(self, session: AsyncSession) -> None:
        """Получает tenant-сессию внешнего UoW."""
        self.session = session

    async def used_images(
        self, query: FindUsedImageFilesQuery
    ) -> FindUsedImageFilesResultDTO:
        """Возвращает используемые файлы, включая галереи всех локалей."""
        ids = await self.session.scalars(
            select(CatalogItemImageModel.file_id)
            .where(CatalogItemImageModel.file_id.in_(query.file_ids))
            .distinct()
        )
        return FindUsedImageFilesResultDTO(tuple(ids))
