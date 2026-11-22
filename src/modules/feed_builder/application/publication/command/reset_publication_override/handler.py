from src.modules.feed_builder.application.publication.command.reset_publication_override.command import (
    ResetPublicationOverrideCommand,
)
from src.modules.feed_builder.application.publication.command.reset_publication_override.dto import (
    ResetPublicationOverrideResultDTO,
)
from src.modules.feed_builder.application.publication.override_target import (
    load_override_target,
)
from src.modules.feed_builder.domain.feed.repository import FeedRepositoryProtocol
from src.modules.feed_builder.domain.publication.repository import (
    FeedPublicationRepositoryProtocol,
)
from src.modules.shared.domain.time.clock_port import ClockPort


class ResetPublicationOverrideHandler:
    """Выполняет изменение override в общей транзакции публикации."""

    def __init__(
        self,
        feeds: FeedRepositoryProtocol,
        publications: FeedPublicationRepositoryProtocol,
        clock: ClockPort,
    ) -> None:
        """Получает порты общей транзакции."""
        self._feeds, self._publications, self._clock = feeds, publications, clock

    async def execute(
        self, command: ResetPublicationOverrideCommand
    ) -> ResetPublicationOverrideResultDTO:
        """Проверяет текущую схему и обновляет одно поле."""
        original, field = await load_override_target(
            self._feeds,
            self._publications,
            feed_id=command.feed_id,
            publication_id=command.publication_id,
            field_id=command.field_id,
            expected_feed_version=command.expected_feed_version,
            expected_version=command.expected_version,
        )
        result = original.reset_override(field.id, now=self._clock.now())
        if result is not original:
            await self._publications.save(result, original.version)
        return ResetPublicationOverrideResultDTO(result.version.value)
