from src.modules.feed_builder.application.feed.command.archive_feed.command import (
    ArchiveFeedCommand,
)
from src.modules.feed_builder.application.feed.port.settings_repository import (
    FeedSettingsRepositoryProtocol,
)
from src.modules.feed_builder.domain.feed.enum.feed_status import FeedStatus
from src.modules.feed_builder.domain.feed.value_object.feed_version import FeedVersionVO
from src.modules.feed_builder.domain.feed.error import FeedVersionConflictError
from src.modules.shared.domain.time.clock_port import ClockPort


class ArchiveFeedHandler:
    """Сохраняет архивное состояние в общей транзакции без удаления строки."""

    def __init__(
        self, repository: FeedSettingsRepositoryProtocol, clock: ClockPort
    ) -> None:
        """Принимает репозиторий и источник времени."""
        self._repository = repository
        self._clock = clock

    async def execute(self, command: ArchiveFeedCommand) -> None:
        """Архивирует ожидаемую версию; повтор удаления архива идемпотентен."""
        expected = FeedVersionVO(command.expected_version)
        locked = await self._repository.get_settings_for_update(command.feed_id)
        original = locked.feed
        if original.status is FeedStatus.ARCHIVED:
            return
        if original.version != expected:
            raise FeedVersionConflictError("Feed уже изменён.")
        result = original.archive(now=self._clock.now())
        await self._repository.save_settings(result, expected_version=expected)
