from src.modules.feed_builder.domain.feed.aggregate import Feed
from src.modules.feed_builder.domain.feed.enum.feed_status import FeedStatus
from src.modules.feed_builder.domain.feed.enum.feed_product_mode import FeedProductMode
from src.modules.feed_builder.domain.feed.value_object.feed_version import FeedVersionVO
from src.modules.feed_builder.domain.feed.error import (
    FeedArchivedError,
    FeedVersionConflictError,
)
from src.modules.feed_builder.domain.publication.error import (
    InvalidPublicationValueError,
)


class PublicationParticipationPolicy:
    """Проверяет участие по состоянию Feed без владения внешними источниками."""

    @staticmethod
    def ensure_editable(
        feed: Feed, expected_version: FeedVersionVO | None = None
    ) -> None:
        """Не меняет Feed при добавлении или смене статуса самостоятельной публикации."""
        if expected_version is not None and feed.version != expected_version:
            raise FeedVersionConflictError("Feed уже изменён.")
        if feed.status is FeedStatus.ARCHIVED:
            raise FeedArchivedError("Архивный Feed доступен только для просмотра.")
        if feed.export_settings.product_mode is not FeedProductMode.VARIABLE_TO_SINGLE:
            raise InvalidPublicationValueError("Неподдержанный режим товаров.")
