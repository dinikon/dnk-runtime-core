from dataclasses import dataclass
from typing import Protocol

from src.modules.feed_builder.application.feed.types import JsonObject
from src.modules.feed_builder.domain.feed.aggregate import Feed
from src.modules.feed_builder.domain.feed.value_object.feed_id import FeedIdVO
from src.modules.feed_builder.domain.feed.value_object.feed_version import FeedVersionVO


@dataclass(frozen=True, slots=True)
class LockedFeedSettings:
    """Передаёт настройки агрегата и непрозрачную проекцию графа для HTTP."""

    feed: Feed
    graph_document: JsonObject


class FeedSettingsRepositoryProtocol(Protocol):
    """Позволяет управлять фидом независимо от версии его графа."""

    async def get_settings_for_update(self, feed_id: FeedIdVO) -> LockedFeedSettings:
        """Блокирует строку фида и читает только типизированные настройки."""
        ...

    async def save_settings(
        self, feed: Feed, *, expected_version: FeedVersionVO
    ) -> None:
        """Обновляет настройки и версию, оставляя документ графа на месте."""
        ...
