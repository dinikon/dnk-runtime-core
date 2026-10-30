from datetime import datetime
from uuid import UUID

from src.modules.channels.application.content_feed.port.query_repository import (
    ContentFeedQueryRepositoryProtocol,
)
from src.modules.channels.application.content_feed.port.jobs import FeedImportJobsPort
from src.modules.channels.domain.content_feed.error import ContentFeedError


class FeedImportDeletionGuard:
    """Координирует удаление Channel с принадлежащими ему активными импортами."""

    def __init__(
        self, queries: ContentFeedQueryRepositoryProtocol, jobs: FeedImportJobsPort
    ) -> None:
        """Использует проекции и задания того же UoW."""
        self.queries, self.jobs = queries, jobs

    async def require_channel_deletable(
        self, *, tenant_id: UUID, channel_id: UUID, now: datetime
    ) -> None:
        """Не теряет связь с неразрешённым внешним импортом при каскадном удалении."""
        if any(state.busy for state in await self.queries.import_states(channel_id)):
            raise ContentFeedError("feed_import_active", conflict=True)
        await self.jobs.cancel_channel(
            tenant_id=tenant_id, channel_id=channel_id, now=now
        )
