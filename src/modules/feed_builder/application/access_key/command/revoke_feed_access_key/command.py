from dataclasses import dataclass

from src.modules.feed_builder.domain.access_key.value_object.feed_access_key_id import (
    FeedAccessKeyIdVO,
)
from src.modules.feed_builder.domain.feed.value_object.feed_id import FeedIdVO


@dataclass(frozen=True, slots=True)
class RevokeFeedAccessKeyCommand:
    """Указывает конкретный ключ в границах одного фида."""

    feed_id: FeedIdVO
    key_id: FeedAccessKeyIdVO
