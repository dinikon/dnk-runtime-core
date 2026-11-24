from typing import Protocol

from src.modules.feed_builder.application.feed.service.publication_export import (
    ExportRecord,
    PublicationExportContext,
)
from src.modules.feed_builder.application.publication.port.export_source import (
    PublicationCursor,
)


class FeedRefreshBatchReaderPort(Protocol):
    """Читает расчётные пакеты в независимых коротких транзакциях."""

    async def read_batch(
        self,
        context: PublicationExportContext,
        cursor: PublicationCursor | None,
        limit: int,
    ) -> tuple[tuple[ExportRecord, ...], PublicationCursor | None]:
        """Возвращает результаты пакета и курсор продолжения."""
        ...
