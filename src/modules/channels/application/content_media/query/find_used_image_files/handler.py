from src.modules.channels.application.content_media.port.query_repository import (
    ContentMediaQueryRepositoryProtocol,
)
from src.modules.channels.application.content_media.query.find_used_image_files.query import (
    FindUsedImageFilesQuery,
)
from src.modules.channels.application.content_media.query.find_used_image_files.dto import (
    FindUsedImageFilesResultDTO,
)


class FindUsedImageFilesHandler:
    """Публичное чтение ссылок Channels без блокировки агрегатов."""

    def __init__(self, queries: ContentMediaQueryRepositoryProtocol) -> None:
        """Получает проекции общей tenant-сессии."""
        self._queries = queries

    async def execute(
        self, query: FindUsedImageFilesQuery
    ) -> FindUsedImageFilesResultDTO:
        """Учитывает сохранённые overrides и выполняемые передачи."""
        return FindUsedImageFilesResultDTO(
            await self._queries.used_images(query.file_ids)
        )
