from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.channels.application.channel.command.create_connection.command import (
    CreateConnectionCommand,
)
from src.modules.channels.application.channel.command.create_connection.dto import (
    CreateConnectionResultDTO,
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
from src.modules.shared.application.uuid.uuid_port import UUIdGeneratorProtocol


class CreateConnectionHandler:
    """Валидирует настройки и атомарно ставит проверку единственного Connection."""

    def __init__(
        self,
        channels: ChannelRepositoryProtocol,
        workflow: ConnectionWorkflow,
        registry: PluginRegistryProtocol,
        references: ConnectionReferencesProtocol,
        secrets: ConnectionSecretsProtocol,
        clock: ClockPort,
        identifiers: UUIdGeneratorProtocol,
    ) -> None:
        """Принимает абстрактные порты без SQLAlchemy и HTTP."""
        self.channels, self.workflow, self.registry = (channels, workflow, registry)
        self.references, self.secrets, self.clock, self.identifiers = (
            references,
            secrets,
            clock,
            identifiers,
        )

    async def execute(
        self, command: CreateConnectionCommand
    ) -> CreateConnectionResultDTO:
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
        connection_id = self.identifiers.new()
        ciphertext = self.secrets.seal(
            command.tenant_id, connection_id, command.credentials
        )
        channel.attach_connection(
            EntityIdVO.from_value(connection_id),
            command.settings,
            ciphertext,
            EntityIdVO.from_value(command.actor_id),
            self.clock.now(),
        )
        job_id = await self.workflow.verify(
            command.tenant_id, channel, command.actor_id
        )
        return CreateConnectionResultDTO(
            channel.id.uuid, connection_id, channel.revision, job_id
        )
