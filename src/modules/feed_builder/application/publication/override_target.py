from uuid import UUID

from src.modules.feed_builder.application.publication.participation import (
    load_publication_for_update,
)
from src.modules.feed_builder.domain.feed.entity.field_definition import FieldDefinition
from src.modules.feed_builder.domain.feed.repository import FeedRepositoryProtocol
from src.modules.feed_builder.domain.feed.value_object.feed_id import FeedIdVO
from src.modules.feed_builder.domain.feed.value_object.feed_version import FeedVersionVO
from src.modules.feed_builder.domain.publication.aggregate import FeedPublication
from src.modules.feed_builder.domain.publication.error import (
    InvalidPublicationValueError,
)
from src.modules.feed_builder.domain.publication.policy.participation import (
    PublicationParticipationPolicy,
)
from src.modules.feed_builder.domain.publication.repository import (
    FeedPublicationRepositoryProtocol,
)


async def load_override_target(
    feeds: FeedRepositoryProtocol,
    publications: FeedPublicationRepositoryProtocol,
    *,
    feed_id: UUID,
    publication_id: UUID,
    field_id: UUID,
    expected_feed_version: int,
    expected_version: int,
) -> tuple[FeedPublication, FieldDefinition]:
    """Фиксирует схему и публикацию в установленном порядке блокировок."""
    feed = await feeds.get_for_update(FeedIdVO(feed_id))
    PublicationParticipationPolicy.ensure_editable(
        feed, FeedVersionVO(expected_feed_version)
    )
    publication = await load_publication_for_update(
        publications, feed, publication_id, expected_version
    )
    field = next(
        (item for item in feed.schema.fields if item.id.uuid == field_id), None
    )
    if field is None:
        raise InvalidPublicationValueError(
            "Поле отсутствует в сохранённой схеме.", path=("field_id",)
        )
    return publication, field
