from datetime import datetime
from typing import Protocol
from uuid import UUID

from src.modules.feed_builder.application.export_state.query.dto import (
    FeedExportIssuesPageDTO,
    FeedExportStateDTO,
    PublicFeedFileDTO,
)
from src.modules.feed_builder.domain.feed.enum.export_format import ExportFormat
from src.modules.feed_builder.domain.access_key.value_object.access_token_hash import (
    AccessTokenHashVO,
)


class FeedExportQueryRepositoryProtocol(Protocol):
    """Читает только нужные проекции на доверенной tenant-сессии."""

    async def get(self, feed_id: UUID) -> FeedExportStateDTO | None:
        """Возвращает доступное состояние существующего Feed."""
        ...

    async def list_issues(
        self, feed_id: UUID, severity: str | None, limit: int, offset: int
    ) -> FeedExportIssuesPageDTO:
        """Возвращает диагностики последнего отчёта."""
        ...

    async def get_public_file(
        self,
        link_id: UUID,
        format: ExportFormat,
        *,
        token_hash: AccessTokenHashVO | None,
        now: datetime,
    ) -> PublicFeedFileDTO | None:
        """Находит доступный активный файл по адресу и формату с учётом токена."""
        ...

    async def used_file_ids(self, file_ids: tuple[UUID, ...]) -> tuple[UUID, ...]:
        """Возвращает ссылки, которые защищают файл от удаления."""
        ...
