from src.modules.channels.application.channel.error import (
    ChannelFieldError,
    ChannelValidationError,
)
from src.modules.channels.application.channel.command.update_channel.dto import (
    UpdateChannelResultDTO,
)
from src.modules.channels.application.channel.command.update_channel.command import (
    UpdateChannelCommand,
)
from src.modules.channels.application.channel.port.registry import ChannelRegistryPort
from src.modules.channels.application.channel.port.validation import (
    ConnectionValidatorPort,
)
from src.modules.channels.application.channel.port.secret_cipher import SecretCipherPort
from src.modules.channels.application.channel.settings import (
    require_writable,
    seal_settings,
)
from src.modules.channels.domain.channel.error import (
    ChannelNotFoundError,
)
from src.modules.channels.domain.channel.repository import ChannelRepositoryProtocol
from src.modules.channels.domain.channel.value_object.identifier import ChannelIdVO
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.shared.domain.time.clock_port import ClockPort


class UpdateChannelHandler:
    """Координирует блокировку канала, объединение настроек и доменные изменения."""

    def __init__(
        self,
        repository: ChannelRepositoryProtocol,
        registry: ChannelRegistryPort,
        validator: ConnectionValidatorPort,
        cipher: SecretCipherPort,
        clock: ClockPort,
    ) -> None:
        """Принимает порты, собранные во внешнем контексте выполнения."""
        self._repository, self._registry, self._validator, self._cipher, self._clock = (
            repository,
            registry,
            validator,
            cipher,
            clock,
        )

    async def execute(self, command: UpdateChannelCommand) -> UpdateChannelResultDTO:
        """Применяет команду через агрегат и возвращает результат без выполнения commit."""
        channel = await self._repository.get_for_update(
            ChannelIdVO.from_value(command.channel_id)
        )
        if channel is None:
            raise ChannelNotFoundError("Channel not found.")
        actor_id = EntityIdVO.from_value(command.actor_id)
        now = self._clock.now()
        if command.connection_settings is not None:
            if command.config_version is None:
                raise ChannelValidationError(
                    (
                        ChannelFieldError(
                            path=("config_version",),
                            message="Configuration version is required.",
                            code="missing",
                        ),
                    )
                )
            definition = self._registry.get(channel.kind)
            require_writable(definition, command.config_version)
            current = dict(channel.settings.public) | self._cipher.decrypt(
                channel.settings.encrypted_secrets
            )
            candidate = current | command.connection_settings
            self._validator.validate(definition, candidate)
            if (
                candidate != current
                or channel.config_version != definition.config_version
            ):
                channel = channel.change_settings(
                    seal_settings(definition, candidate, self._cipher),
                    definition.config_version,
                    actor_id=actor_id,
                    now=now,
                )
        if command.name is not None:
            channel = channel.rename(command.name, actor_id=actor_id, now=now)
        if command.is_active is not None:
            channel = channel.set_active(command.is_active, actor_id=actor_id, now=now)
        await self._repository.save(channel)
        return UpdateChannelResultDTO.from_channel(
            channel, self._registry.get(channel.kind).type
        )
