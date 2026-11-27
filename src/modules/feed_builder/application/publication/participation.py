from uuid import UUID
from src.modules.feed_builder.domain.feed.aggregate import Feed
from src.modules.feed_builder.application.feed.port.settings_repository import (
    FeedSettingsRepositoryProtocol,
)
from src.modules.feed_builder.domain.feed.value_object.feed_id import FeedIdVO
from src.modules.feed_builder.domain.publication.repository import (
    FeedPublicationRepositoryProtocol,
)
from src.modules.feed_builder.domain.publication.aggregate import FeedPublication
from src.modules.feed_builder.domain.publication.value_object.feed_publication_id import (
    FeedPublicationIdVO,
)
from src.modules.feed_builder.domain.publication.value_object.feed_publication_version import (
    FeedPublicationVersionVO,
)
from src.modules.feed_builder.domain.publication.policy.participation import (
    PublicationParticipationPolicy,
)
from src.modules.feed_builder.domain.publication.error import (
    PublicationNotFoundError,
    PublicationVersionConflictError,
)


async def load_editable_publication(
    feeds: FeedSettingsRepositoryProtocol,
    publications: FeedPublicationRepositoryProtocol,
    feed_id: UUID,
    identifier: UUID,
    expected_version: int,
) -> FeedPublication:
    """Загружает и проверяет объекты в едином порядке блокировок Feed → Publication."""
    feed = (await feeds.get_settings_for_update(FeedIdVO(feed_id))).feed
    PublicationParticipationPolicy.ensure_editable(feed)
    return await load_publication_for_update(
        publications, feed, identifier, expected_version
    )


async def load_publication_for_update(
    publications: FeedPublicationRepositoryProtocol,
    feed: Feed,
    identifier: UUID,
    expected_version: int,
) -> FeedPublication:
    """Проверяет принадлежность и версию публикации после блокировки её Feed."""
    publication = await publications.get_for_update(FeedPublicationIdVO(identifier))
    if publication.feed_id != feed.id:
        raise PublicationNotFoundError("Публикация не найдена в Feed.")
    if publication.version != FeedPublicationVersionVO(expected_version):
        raise PublicationVersionConflictError("Публикация уже изменена.")
    return publication
