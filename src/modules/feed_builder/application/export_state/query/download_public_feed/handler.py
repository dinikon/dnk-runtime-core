from uuid import UUID

from src.modules.feed_builder.application.export_state.port.file_content import (
    ExportFileContentDTO,
    FeedExportContentPort,
)
from src.modules.feed_builder.application.export_state.port.query_repository import (
    FeedExportQueryRepositoryProtocol,
)
from src.modules.feed_builder.application.export_state.query.download_public_feed.query import (
    DownloadPublicFeedQuery,
)
from src.modules.feed_builder.application.export_state.query.dto import (
    PublicFeedFileDTO,
)


class DownloadPublicFeedHandler:
    """Разрешает текущую ссылку и читает только связанный с ней файл."""

    def __init__(
        self, queries: FeedExportQueryRepositoryProtocol, files: FeedExportContentPort
    ) -> None:
        """Получает read-side и порт потокового доступа."""
        self._queries, self._files = queries, files

    async def execute(self, query: DownloadPublicFeedQuery) -> PublicFeedFileDTO | None:
        """Проверяет адрес до обработки условного HTTP-запроса."""
        return await self._queries.get_public_file(query.public_link_id, query.format)

    async def open_file(
        self, tenant_id: UUID, file: PublicFeedFileDTO
    ) -> ExportFileContentDTO:
        """Открывает уже разрешённый активный файл текущего tenant."""
        return await self._files.open(tenant_id, file.file_id)
