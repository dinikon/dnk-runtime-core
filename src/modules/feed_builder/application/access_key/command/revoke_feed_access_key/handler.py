from src.modules.feed_builder.application.access_key.command.revoke_feed_access_key.command import (
    RevokeFeedAccessKeyCommand,
)
from src.modules.feed_builder.domain.access_key.repository import (
    FeedAccessKeyRepositoryProtocol,
)
from src.modules.shared.domain.time.clock_port import ClockPort


class RevokeFeedAccessKeyHandler:
    """Отзывает только указанный ключ фида."""

    def __init__(self, keys: FeedAccessKeyRepositoryProtocol, clock: ClockPort) -> None:
        """Принимает репозиторий записи и часы."""
        self._keys, self._clock = keys, clock

    async def execute(self, command: RevokeFeedAccessKeyCommand) -> None:
        """Сохраняет отзыв под блокировкой ключа и поддерживает повтор запроса."""
        key = await self._keys.get_for_update(command.feed_id, command.key_id)
        revoked = key.revoke(now=self._clock.now())
        if key is not revoked:
            await self._keys.save(revoked)
