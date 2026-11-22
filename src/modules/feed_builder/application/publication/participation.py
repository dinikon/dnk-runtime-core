from uuid import UUID
from src.modules.feed_builder.domain.feed.repository import FeedRepositoryProtocol
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
    feeds: FeedRepositoryProtocol,
    publications: FeedPublicationRepositoryProtocol,
    feed_id: UUID,
    identifier: UUID,
    expected_version: int,
) -> FeedPublication:
    """Загружает и проверяет объекты в едином порядке блокировок Feed → Publication."""
    feed = await feeds.get_for_update(FeedIdVO(feed_id))
    PublicationParticipationPolicy.ensure_editable(feed)
    publication = await publications.get_for_update(FeedPublicationIdVO(identifier))
    if publication.feed_id != feed.id:
        raise PublicationNotFoundError("Публикация не найдена в Feed.")
    if publication.version != FeedPublicationVersionVO(expected_version):
        raise PublicationVersionConflictError("Публикация уже изменена.")
    return publication
