from src.modules.feed_builder.application.export_state.command.rotate_feed_public_link.command import (
    RotateFeedPublicLinkCommand,
)
from src.modules.feed_builder.application.export_state.command.rotate_feed_public_link.dto import (
    RotateFeedPublicLinkResultDTO,
)
from src.modules.feed_builder.domain.export_state.repository import (
    FeedExportStateRepositoryProtocol,
)
from src.modules.feed_builder.domain.feed.error import (
    FeedVersionConflictError,
    InvalidFeedValueError,
)
from src.modules.feed_builder.domain.feed.repository import FeedRepositoryProtocol
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
        feeds: FeedRepositoryProtocol,
        states: FeedExportStateRepositoryProtocol,
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
        feed = await self._feeds.get_for_update(FeedIdVO(command.feed_id))
        if feed.version.value != command.expected_version:
            raise FeedVersionConflictError("Feed уже изменён.")
        state = await self._states.get_for_update(feed.id)
        if state.active is None:
            raise InvalidFeedValueError("Сначала опубликуйте файл.")
        link = FeedPublicLinkIdVO(self._identifiers.new())
        changed = feed.rotate_public_link(link, now=self._clock.now())
        await self._feeds.save(changed, expected_version=feed.version)
        return RotateFeedPublicLinkResultDTO(
            link.uuid, state.active.format, changed.version.value
        )
