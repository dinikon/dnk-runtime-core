from src.modules.feed_builder.application.publication.command.change_publication_status.command import (
    ChangePublicationStatusCommand,
)
from src.modules.feed_builder.application.publication.command.change_publication_status.dto import (
    ChangePublicationStatusResultDTO,
)
from src.modules.feed_builder.domain.publication.enum.publication_status import (
    PublicationStatus,
)
from src.modules.feed_builder.application.publication.participation import (
    load_editable_publication,
)
from src.modules.feed_builder.domain.feed.repository import FeedRepositoryProtocol
from src.modules.feed_builder.domain.publication.repository import (
    FeedPublicationRepositoryProtocol,
)
from src.modules.shared.domain.time.clock_port import ClockPort
from src.modules.feed_builder.domain.publication.error import (
    InvalidPublicationValueError,
)


class ChangePublicationStatusHandler:
    """Координирует изменение участия через метод агрегата в общем UoW."""

    def __init__(
        self,
        feeds: FeedRepositoryProtocol,
        publications: FeedPublicationRepositoryProtocol,
        clock: ClockPort,
    ) -> None:
        """Принимает только нужные порты процесса."""
        self._feeds, self._publications, self._clock = feeds, publications, clock

    async def execute(
        self, command: ChangePublicationStatusCommand
    ) -> ChangePublicationStatusResultDTO:
        """Сохраняет только фактический переход без перезаписи overrides."""
        if command.status not in (PublicationStatus.ENABLED, PublicationStatus.PAUSED):
            raise InvalidPublicationValueError("Допустимы ENABLED и PAUSED.")
        original = await load_editable_publication(
            self._feeds,
            self._publications,
            command.feed_id,
            command.publication_id,
            command.expected_version,
        )
        result = (
            original.enable(now=self._clock.now())
            if command.status is PublicationStatus.ENABLED
            else original.pause(now=self._clock.now())
        )
        if result is not original:
            await self._publications.save(result, original.version)
        return ChangePublicationStatusResultDTO(
            result.id.uuid, result.status.value, result.version.value, result.updated_at
        )
