from src.modules.channels.application.command.update_channel.command import (
    UpdateChannelCommand,
)
from src.modules.channels.application.port.registry import ChannelRegistryPort
from src.modules.channels.application.port.validation import ConnectionValidatorPort
from src.modules.channels.application.port.secret_cipher import SecretCipherPort
from src.modules.channels.application.settings import require_writable, seal_settings
from src.modules.channels.domain.error import (
    ChannelNotFoundError,
    ChannelValidationError,
)
from src.modules.channels.domain.repository import ChannelRepositoryProtocol
from src.modules.channels.domain.value_object.identifier import ChannelIdVO
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.shared.domain.time.clock_port import ClockPort


class UpdateChannelHandler:
    def __init__(
        self,
        repository: ChannelRepositoryProtocol,
        registry: ChannelRegistryPort,
        validator: ConnectionValidatorPort,
        cipher: SecretCipherPort,
        clock: ClockPort,
    ):
        self.repository, self.registry, self.validator, self.cipher, self.clock = (
            repository,
            registry,
            validator,
            cipher,
            clock,
        )

    async def execute(self, command: UpdateChannelCommand):
        channel = await self.repository.get_for_update(
            ChannelIdVO.from_value(command.channel_id)
        )
        if channel is None:
            raise ChannelNotFoundError("Channel not found.")
        audit = dict(
            actor_id=EntityIdVO.from_value(command.actor_id), now=self.clock.now()
        )
        if command.connection_settings is not None:
            if command.config_version is None:
                raise ChannelValidationError(
                    (
                        {
                            "loc": ["body", "config_version"],
                            "msg": "Configuration version is required.",
                            "type": "missing",
                        },
                    )
                )
            definition = self.registry.get(channel.kind)
            require_writable(definition, command.config_version)
            current = dict(channel.settings.public) | self.cipher.decrypt(
                channel.settings.encrypted_secrets
            )
            candidate = current | command.connection_settings
            self.validator.validate(definition, candidate)
            if candidate != current:
                channel = channel.change_settings(
                    seal_settings(definition, candidate, self.cipher),
                    definition.config_version,
                    **audit,
                )
        if command.name is not None:
            channel = channel.rename(command.name, **audit)
        if command.is_active is not None:
            channel = channel.set_active(command.is_active, **audit)
        await self.repository.save(channel)
        return channel.id.uuid
