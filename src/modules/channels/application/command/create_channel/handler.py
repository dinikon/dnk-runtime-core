from src.modules.channels.application.command.create_channel.command import (
    CreateChannelCommand,
)
from src.modules.channels.application.port.registry import ChannelRegistryPort
from src.modules.channels.application.port.validation import ConnectionValidatorPort
from src.modules.channels.application.port.secret_cipher import SecretCipherPort
from src.modules.channels.application.settings import require_writable, seal_settings
from src.modules.channels.domain.error import ChannelNotFoundError, InvalidChannelError
from src.modules.channels.domain.aggregate import Channel
from src.modules.channels.domain.repository import ChannelRepositoryProtocol
from src.modules.channels.domain.value_object.identifier import ChannelIdVO
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.shared.domain.time.clock_port import ClockPort
from src.modules.shared.application.uuid.uuid_port import UUIdGeneratorProtocol


class CreateChannelHandler:
    def __init__(
        self,
        repository: ChannelRepositoryProtocol,
        registry: ChannelRegistryPort,
        validator: ConnectionValidatorPort,
        cipher: SecretCipherPort,
        clock: ClockPort,
        uuids: UUIdGeneratorProtocol,
    ):
        (
            self.repository,
            self.registry,
            self.validator,
            self.cipher,
            self.clock,
            self.uuids,
        ) = (repository, registry, validator, cipher, clock, uuids)

    async def execute(self, command: CreateChannelCommand):
        try:
            definition = self.registry.get(command.kind)
        except ChannelNotFoundError:
            raise InvalidChannelError("Unknown channel platform.") from None
        require_writable(definition, command.config_version)
        self.validator.validate(definition, command.connection_settings)
        channel = Channel.create(
            channel_id=ChannelIdVO.from_value(self.uuids.new()),
            name=command.name,
            kind=definition.kind,
            config_version=definition.config_version,
            settings=seal_settings(
                definition, command.connection_settings, self.cipher
            ),
            is_active=command.is_active,
            actor_id=EntityIdVO.from_value(command.actor_id),
            now=self.clock.now(),
        )
        await self.repository.add(channel)
        return channel.id.uuid
