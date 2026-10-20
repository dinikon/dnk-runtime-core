from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.channels.domain.channel.repository import ChannelRepositoryProtocol
from src.modules.channels.domain.sync_run.repository import SyncRunRepositoryProtocol
from src.modules.channels.application.plugin_contract import ResourceSettingsDTO
from src.modules.channels.application.sync_run.command.prepare_publication_initialization.command import (
    PreparePublicationInitializationCommand,
)
from src.modules.channels.application.sync_run.command.prepare_publication_initialization.dto import (
    PreparePublicationInitializationResultDTO,
)


class PreparePublicationInitializationHandler:
    """Координирует конкретный шаг prepare_publication_initialization."""

    def __init__(
        self, channels: ChannelRepositoryProtocol, runs: SyncRunRepositoryProtocol
    ) -> None:
        """Принимает только зависимости, необходимые этому сценарию."""
        self.channels = channels
        self.runs = runs

    async def execute(
        self, command: PreparePublicationInitializationCommand
    ) -> PreparePublicationInitializationResultDTO | None:
        """Сохраняет результат шага без HTTP и самостоятельного commit."""
        from src.modules.channels.application.plugin_contract import (
            ReadPublicationPageInputDTO,
        )

        channel_id = await self.runs.channel_id(EntityIdVO.from_value(command.run_id))
        channel = await self.channels.get(EntityIdVO.from_value(channel_id))
        probe = await self.runs.get(EntityIdVO.from_value(command.run_id))
        connection = channel.require_connection()
        if (
            probe.status not in ("queued", "running")
            or probe.sequence != command.sequence
            or channel.is_archived
            or connection.is_paused
            or (connection.verification_status != "verified")
            or (connection.generation != probe.generation)
        ):
            return None
        return PreparePublicationInitializationResultDTO(
            probe.id.uuid,
            probe.actor_id.uuid,
            channel.id.uuid,
            connection.id.uuid,
            connection.generation,
            channel.platform_kind,
            ReadPublicationPageInputDTO(
                ResourceSettingsDTO(
                    connection.settings.endpoint,
                    connection.settings.options,
                ),
                connection.resource_identity,
                dict(probe.checkpoint),
            ),
            connection.credentials_ciphertext,
        )
