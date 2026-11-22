from src.modules.feed_builder.application.publication.command.remove_publication.command import (
    RemovePublicationCommand,
)
from src.modules.feed_builder.application.publication.participation import (
    load_editable_publication,
)
from src.modules.feed_builder.domain.feed.repository import FeedRepositoryProtocol
from src.modules.feed_builder.domain.publication.repository import (
    FeedPublicationRepositoryProtocol,
)
from src.modules.shared.domain.time.clock_port import ClockPort


class RemovePublicationHandler:
    """Координирует изменение участия через метод агрегата в общем UoW."""

    def __init__(
        self,
        feeds: FeedRepositoryProtocol,
        publications: FeedPublicationRepositoryProtocol,
        clock: ClockPort,
    ) -> None:
        """Принимает только нужные порты процесса."""
        self._feeds, self._publications, self._clock = feeds, publications, clock

    async def execute(self, command: RemovePublicationCommand) -> None:
        """Сохраняет только фактический переход без перезаписи overrides."""

        original = await load_editable_publication(
            self._feeds,
            self._publications,
            command.feed_id,
            command.publication_id,
            command.expected_version,
        )
        result = original.archive(now=self._clock.now())
        if result is not original:
            await self._publications.save(result, original.version)
