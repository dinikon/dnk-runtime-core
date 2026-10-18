from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.channels.application.sync_run.service.initialization import (
    InitializationService,
)
from src.modules.channels.application.channel.command.update_connection_settings.command import (
    UpdateConnectionSettingsCommand,
)
from src.modules.channels.application.channel.command.update_connection_settings.dto import (
    UpdateConnectionSettingsResultDTO,
)
from src.modules.channels.domain.channel.repository import ChannelRepositoryProtocol
from src.modules.channels.application.channel.service.connections import (
    ConnectionWorkflow,
)
from src.modules.channels.application.channel.port.references import (
    ConnectionReferencesProtocol,
)
from src.modules.channels.application.channel.port.secrets import (
    ConnectionSecretsProtocol,
)
from src.modules.channels.application.port.plugin_registry import PluginRegistryProtocol
from src.modules.channels.application.plugin_contract import ResourceSettingsDTO
from src.modules.shared.domain.time.clock_port import ClockPort


class UpdateConnectionSettingsHandler:
    """Валидирует настройки и атомарно ставит проверку единственного Connection."""

    def __init__(
        self,
        channels: ChannelRepositoryProtocol,
        workflow: ConnectionWorkflow,
        initialization: InitializationService,
        registry: PluginRegistryProtocol,
        references: ConnectionReferencesProtocol,
        secrets: ConnectionSecretsProtocol,
        clock: ClockPort,
    ) -> None:
        """Принимает только зависимости, необходимые этому сценарию."""
        self.channels = channels
        self.workflow = workflow
        self.initialization = initialization
        self.registry = registry
        self.references = references
        self.secrets = secrets
        self.clock = clock

    async def execute(
        self, command: UpdateConnectionSettingsCommand
    ) -> UpdateConnectionSettingsResultDTO:
        """Сохраняет настройки и job в одной транзакции без сетевых вызовов."""
        channel = await self.channels.get(EntityIdVO.from_value(command.channel_id))
        channel.ensure_revision(command.revision)
        self.registry.validate(
            channel.platform_kind,
            ResourceSettingsDTO(
                command.settings.endpoint,
                command.settings.locales,
                command.settings.currency,
            ),
            command.credentials,
        )
        await self.references.validate(command.settings)
        connection_id = channel.require_connection().id.uuid
        ciphertext = (
            self.secrets.seal(command.tenant_id, connection_id, command.credentials)
            if command.credentials is not None
            else None
        )
        channel.update_connection(
            command.settings,
            ciphertext,
            EntityIdVO.from_value(command.actor_id),
            self.clock.now(),
        )
        if channel.require_connection().is_paused:
            await self.initialization.cancel_active(channel)
            await self.channels.save(channel)
            job_id = None
        else:
            job_id = await self.workflow.verify(
                command.tenant_id, channel, command.actor_id
            )
        return UpdateConnectionSettingsResultDTO(
            channel.id.uuid, connection_id, channel.revision, job_id
        )
