from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.channels.domain.channel.repository import ChannelRepositoryProtocol
from src.modules.channels.application.sync_run.service.initialization import (
    InitializationService,
)
from src.modules.channels.application.sync_run.command.start_publication_initialization.command import (
    StartPublicationInitializationCommand,
)
from src.modules.channels.application.sync_run.command.start_publication_initialization.dto import (
    StartPublicationInitializationResultDTO,
)


class StartPublicationInitializationHandler:
    """Координирует конкретный шаг start_publication_initialization."""

    def __init__(
        self, channels: ChannelRepositoryProtocol, initialization: InitializationService
    ) -> None:
        """Принимает только зависимости, необходимые этому сценарию."""
        self.channels = channels
        self.initialization = initialization

    async def execute(
        self, command: StartPublicationInitializationCommand
    ) -> StartPublicationInitializationResultDTO:
        """Сохраняет результат шага без HTTP и самостоятельного commit."""
        channel = await self.channels.by_connection(
            EntityIdVO.from_value(command.connection_id)
        )
        run = await self.initialization.start(
            command.tenant_id, channel, command.actor_id, command.request_key
        )
        return StartPublicationInitializationResultDTO(
            run.id.uuid, run.status, run.job_id.uuid if run.job_id else None
        )
