from src.modules.feed_builder.application.feed.command.change_feed_access_mode.command import (
    ChangeFeedAccessModeCommand,
)
from src.modules.feed_builder.application.feed.command.change_feed_access_mode.dto import (
    ChangedFeedAccessModeDTO,
)
from src.modules.feed_builder.application.feed.port.settings_repository import (
    FeedSettingsRepositoryProtocol,
)
from src.modules.feed_builder.domain.feed.error import FeedVersionConflictError
from src.modules.feed_builder.domain.feed.value_object.feed_version import FeedVersionVO
from src.modules.shared.domain.time.clock_port import ClockPort


class ChangeFeedAccessModeHandler:
    """Меняет политику публикации для уже доступного или будущего файла."""

    def __init__(self, feeds: FeedSettingsRepositoryProtocol, clock: ClockPort) -> None:
        """Принимает настройки под блокировкой и часы."""
        self._feeds, self._clock = feeds, clock

    async def execute(
        self, command: ChangeFeedAccessModeCommand
    ) -> ChangedFeedAccessModeDTO:
        """Атомарно сохраняет выбранный режим без чтения графа."""
        expected = FeedVersionVO(command.expected_version)
        feed = (await self._feeds.get_settings_for_update(command.feed_id)).feed
        if feed.version != expected:
            raise FeedVersionConflictError("Feed уже изменён.")
        updated = feed.change_access_mode(command.access_mode, now=self._clock.now())
        if updated is not feed:
            await self._feeds.save_settings(updated, expected_version=expected)
        return ChangedFeedAccessModeDTO(updated.access_mode, updated.version.value)
