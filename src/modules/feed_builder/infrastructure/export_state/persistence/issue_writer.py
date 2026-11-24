from collections.abc import Iterable
from itertools import batched
from uuid import UUID

from sqlalchemy import delete, insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.feed_builder.application.export_state.issue import FeedExportIssueDTO
from src.modules.feed_builder.infrastructure.persistence.models.export_state import (
    FeedExportIssueModel,
)
from src.modules.shared.application.uuid.uuid_port import UUIdGeneratorProtocol


class SqlAlchemyFeedExportIssueWriter:
    """Хранит только диагностики последней проверки в текущем UoW."""

    def __init__(self, session: AsyncSession, ids: UUIdGeneratorProtocol) -> None:
        """Получает сессию завершения и генератор ID для диагностики."""
        self._session = session
        self._ids = ids

    async def replace(
        self, feed_id: UUID, issues: Iterable[FeedExportIssueDTO]
    ) -> None:
        """Заменяет отчёт пакетной вставкой с ограниченной памятью."""
        await self._session.execute(
            delete(FeedExportIssueModel).where(FeedExportIssueModel.feed_id == feed_id)
        )
        for batch in batched(issues, 500):
            await self._session.execute(
                insert(FeedExportIssueModel),
                [
                    {
                        "id": self._ids.new(),
                        "feed_id": feed_id,
                        "publication_id": issue.publication_id,
                        "severity": issue.severity,
                        "code": issue.code,
                        "message": issue.message,
                        "sku": issue.sku,
                        "field_id": issue.field_id,
                        "rule_id": issue.rule_id,
                        "path": list(issue.path),
                    }
                    for issue in batch
                ],
            )
