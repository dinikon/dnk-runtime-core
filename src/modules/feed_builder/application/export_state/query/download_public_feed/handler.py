from src.modules.feed_builder.application.export_state.port.file_content import (
    ExportFileContentDTO,
    FeedExportContentPort,
)
from src.modules.feed_builder.application.export_state.port.public_feed_tenant import (
    PublicFeedTenantResolverPort,
)
from src.modules.feed_builder.application.export_state.port.query_repository import (
    FeedExportQueryRepositoryProtocol,
)
from src.modules.feed_builder.application.export_state.query.download_public_feed.dto import (
    DownloadPublicFeedResultDTO,
)
from src.modules.feed_builder.application.export_state.query.download_public_feed.query import (
    DownloadPublicFeedQuery,
)
from src.modules.shared.domain.time.clock_port import ClockPort


class DownloadPublicFeedHandler:
    """Разрешает текущую ссылку и читает только связанный с ней файл."""

    def __init__(
        self,
        tenants: PublicFeedTenantResolverPort,
        queries: FeedExportQueryRepositoryProtocol,
        files: FeedExportContentPort,
        clock: ClockPort,
    ) -> None:
        """Получает порты разрешения tenant, чтения фида и открытия файла."""
        self._tenants = tenants
        self._queries = queries
        self._files = files
        self._clock = clock

    async def execute(
        self, query: DownloadPublicFeedQuery
    ) -> DownloadPublicFeedResultDTO | None:
        """Проверяет tenant и публичный адрес до открытия файла."""
        tenant_id = await self._tenants.resolve(query.host)
        if tenant_id is None:
            return None
        file = await self._queries.get_public_file(
            query.public_link_id,
            query.format,
            token_hash=query.token_hash,
            now=self._clock.now(),
        )
        if file is None:
            return None
        return DownloadPublicFeedResultDTO(
            tenant_id, file.file_id, file.published_at, file.access_mode
        )

    async def open_file(
        self, file: DownloadPublicFeedResultDTO
    ) -> ExportFileContentDTO:
        """Открывает уже разрешённый активный файл текущего tenant."""
        return await self._files.open(file.tenant_id, file.file_id)
