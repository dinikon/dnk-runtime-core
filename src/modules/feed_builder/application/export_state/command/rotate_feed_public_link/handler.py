from src.modules.feed_builder.application.export_state.command.rotate_feed_public_link.command import (
    RotateFeedPublicLinkCommand,
)
from src.modules.feed_builder.application.export_state.command.rotate_feed_public_link.dto import (
    RotateFeedPublicLinkResultDTO,
)
from src.modules.feed_builder.application.export_state.port.query_repository import (
    FeedExportQueryRepositoryProtocol,
)
from src.modules.feed_builder.domain.feed.enum.export_format import ExportFormat
from src.modules.feed_builder.domain.feed.error import (
    FeedVersionConflictError,
    InvalidFeedValueError,
)
from src.modules.feed_builder.application.feed.port.settings_repository import (
    FeedSettingsRepositoryProtocol,
)
from src.modules.feed_builder.domain.feed.value_object.feed_id import FeedIdVO
from src.modules.feed_builder.domain.feed.value_object.feed_public_link_id import (
    FeedPublicLinkIdVO,
)
from src.modules.shared.application.uuid.uuid_port import UUIdGeneratorProtocol
from src.modules.shared.domain.time.clock_port import ClockPort


class RotateFeedPublicLinkHandler:
    """Меняет ссылку в агрегате Feed под блокировкой."""

    def __init__(
        self,
        feeds: FeedSettingsRepositoryProtocol,
        states: FeedExportQueryRepositoryProtocol,
        clock: ClockPort,
        identifiers: UUIdGeneratorProtocol,
    ) -> None:
        """Собирает сценарий в едином tenant UoW."""
        self._feeds, self._states, self._clock, self._identifiers = (
            feeds,
            states,
            clock,
            identifiers,
        )

    async def execute(
        self, command: RotateFeedPublicLinkCommand
    ) -> RotateFeedPublicLinkResultDTO:
        """Проверяет текущий файл и сохраняет новый адрес."""
        feed = (
            await self._feeds.get_settings_for_update(FeedIdVO(command.feed_id))
        ).feed
        if feed.version.value != command.expected_version:
            raise FeedVersionConflictError("Feed уже изменён.")
        state = await self._states.get(feed.id.uuid)
        if state is None or state.active is None:
            raise InvalidFeedValueError("Сначала опубликуйте файл.")
        link = FeedPublicLinkIdVO(self._identifiers.new())
        changed = feed.rotate_public_link(link, now=self._clock.now())
        await self._feeds.save_settings(changed, expected_version=feed.version)
        return RotateFeedPublicLinkResultDTO(
            link.uuid, ExportFormat(state.active.format), changed.version.value
        )
