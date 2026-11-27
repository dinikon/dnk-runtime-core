from src.modules.feed_builder.application.access_key.command.issue_feed_access_key.command import (
    IssueFeedAccessKeyCommand,
)
from src.modules.feed_builder.application.access_key.command.issue_feed_access_key.dto import (
    IssuedFeedAccessKeyDTO,
)
from src.modules.feed_builder.application.access_key.token import issue_access_token
from src.modules.feed_builder.application.feed.port.settings_repository import (
    FeedSettingsRepositoryProtocol,
)
from src.modules.feed_builder.domain.access_key.aggregate import FeedAccessKey
from src.modules.feed_builder.domain.access_key.repository import (
    FeedAccessKeyRepositoryProtocol,
)
from src.modules.feed_builder.domain.access_key.value_object.access_key_name import (
    AccessKeyNameVO,
)
from src.modules.feed_builder.domain.access_key.value_object.feed_access_key_id import (
    FeedAccessKeyIdVO,
)
from src.modules.feed_builder.domain.feed.enum.feed_status import FeedStatus
from src.modules.feed_builder.domain.feed.error import FeedArchivedError
from src.modules.shared.application.uuid.uuid_port import UUIdGeneratorProtocol
from src.modules.shared.domain.time.clock_port import ClockPort


class IssueFeedAccessKeyHandler:
    """Выпускает новый ключ без смены адреса или режима фида."""

    def __init__(
        self,
        feeds: FeedSettingsRepositoryProtocol,
        keys: FeedAccessKeyRepositoryProtocol,
        clock: ClockPort,
        identifiers: UUIdGeneratorProtocol,
    ) -> None:
        """Получает репозитории общего tenant UoW, часы и генератор ID."""
        self._feeds, self._keys, self._clock, self._identifiers = (
            feeds,
            keys,
            clock,
            identifiers,
        )

    async def execute(
        self, command: IssueFeedAccessKeyCommand
    ) -> IssuedFeedAccessKeyDTO:
        """Сохраняет digest ключа, возвращая исходный секрет вызывающему."""
        feed = (await self._feeds.get_settings_for_update(command.feed_id)).feed
        if feed.status is FeedStatus.ARCHIVED:
            raise FeedArchivedError("Архивный Feed нельзя редактировать.")
        token, digest = issue_access_token()
        key = FeedAccessKey.create(
            identifier=FeedAccessKeyIdVO(self._identifiers.new()),
            feed_id=feed.id,
            token_hash=digest,
            name=AccessKeyNameVO(command.name),
            expires_at=command.expires_at,
            now=self._clock.now(),
        )
        await self._keys.add(key)
        return IssuedFeedAccessKeyDTO(
            key.id.uuid, key.name.value, key.created_at, key.expires_at, token
        )
