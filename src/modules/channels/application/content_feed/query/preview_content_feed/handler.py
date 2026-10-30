from src.modules.channels.application.content_feed.query.preview_content_feed.query import (
    PreviewContentFeedQuery,
)
from src.modules.channels.application.content_feed.query.preview_content_feed.dto import (
    PreviewContentFeedResultDTO,
    FeedPreviewIssue,
)
from src.modules.channels.application.content_feed.service.management import (
    ContentFeedManagement,
)
from src.modules.channels.application.content_feed.error import FeedBuildError
from src.modules.channels.domain.content_media.error import ContentMediaError
from src.modules.shared.application.persistence.unit_of_work import UnitOfWorkProtocol


class PreviewContentFeedHandler:
    """Проверяет весь документ, сохраняя безопасную диагностику для Console."""

    def __init__(
        self, management: ContentFeedManagement, uow: UnitOfWorkProtocol
    ) -> None:
        """Получает тот же UoW, который используют media и сборка документа."""
        self._management, self._uow = management, uow

    async def execute(
        self, query: PreviewContentFeedQuery
    ) -> PreviewContentFeedResultDTO:
        """При ожидаемом отказе откатывает незавершённые записи до возврата результата."""
        try:
            result = await self._management.preview(
                channel_id=query.channel_id,
                feed_id=query.feed_id,
                actor_id=query.actor_id,
            )
        except FeedBuildError as error:
            await self._uow.rollback()
            return PreviewContentFeedResultDTO(
                False,
                None,
                (FeedPreviewIssue(error.code, error.publication_id, error.field),),
            )
        except ContentMediaError as error:
            await self._uow.rollback()
            return PreviewContentFeedResultDTO(
                False, None, (FeedPreviewIssue(error.code, None, None),)
            )
        return PreviewContentFeedResultDTO(True, result.statistics, ())
