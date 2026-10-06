from src.modules.channels.application.publication_import_run.command.start_publication_import.command import (
    StartPublicationImportCommand,
)
from src.modules.channels.application.publication_import_run.command.start_publication_import.dto import (
    StartPublicationImportResultDTO,
)
from src.modules.channels.application.publication_import_run.service import (
    PublicationImportStarter,
)
from src.modules.channels.domain.channel.repository import ChannelRepositoryProtocol
from src.modules.channels.domain.channel.value_object.identifier import ChannelIdVO
from src.modules.channels.domain.channel.error import ChannelNotFoundError
from src.modules.shared.domain.time.clock_port import ClockPort


class StartPublicationImportHandler:
    """Сериализует запуск импорта через блокировку канала."""

    def __init__(
        self,
        channels: ChannelRepositoryProtocol,
        starter: PublicationImportStarter,
        clock: ClockPort,
    ) -> None:
        """Принимает порты общей транзакции запуска."""
        self._channels, self._starter, self._clock = channels, starter, clock

    async def execute(
        self, command: StartPublicationImportCommand
    ) -> StartPublicationImportResultDTO:
        """Создаёт запуск и durable job до commit внешнего UoW."""
        channel = await self._channels.get_for_update(
            ChannelIdVO.from_value(command.channel_id)
        )
        if channel is None:
            raise ChannelNotFoundError()
        run = await self._starter.start(
            channel=channel, tenant_id=command.tenant_id, now=self._clock.now()
        )
        return StartPublicationImportResultDTO(run.id.uuid)
