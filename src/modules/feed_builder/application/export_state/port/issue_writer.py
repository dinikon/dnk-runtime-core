from collections.abc import Iterable
from typing import Protocol
from uuid import UUID

from src.modules.feed_builder.application.export_state.issue import FeedExportIssueDTO


class FeedExportIssueWriterPort(Protocol):
    """Записывает диагностики последнего отчёта в транзакции его замены."""

    async def replace(
        self, feed_id: UUID, issues: Iterable[FeedExportIssueDTO]
    ) -> None:
        """Удаляет предыдущий отчёт о позициях и сохраняет текущие диагностики."""
        ...
