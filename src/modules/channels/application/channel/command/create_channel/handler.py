from src.modules.channels.application.publication_import_run.service import (
    PublicationImportStarter,
)
from src.modules.channels.domain.channel.value_object.kind import ChannelKind
from src.modules.channels.application.channel.command.create_channel.dto import (
    CreateChannelResultDTO,
)
from src.modules.channels.application.channel.command.create_channel.command import (
    CreateChannelCommand,
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
    InvalidChannelError,
)
from src.modules.channels.domain.channel.aggregate import Channel
from src.modules.channels.domain.channel.repository import ChannelRepositoryProtocol
from src.modules.channels.domain.channel.value_object.identifier import ChannelIdVO
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.shared.domain.time.clock_port import ClockPort
from src.modules.shared.application.uuid.uuid_port import UUIdGeneratorProtocol


class CreateChannelHandler:
    """Координирует создание канала, проверку схемы и защищённое сохранение."""

    def __init__(
        self,
        repository: ChannelRepositoryProtocol,
        registry: ChannelRegistryPort,
        validator: ConnectionValidatorPort,
        cipher: SecretCipherPort,
        clock: ClockPort,
        uuids: UUIdGeneratorProtocol,
        imports: PublicationImportStarter | None = None,
    ) -> None:
        """Принимает порты, собранные во внешнем контексте выполнения."""
        self._imports = imports
        (
            self._repository,
            self._registry,
            self._validator,
            self._cipher,
            self._clock,
            self._uuids,
        ) = (repository, registry, validator, cipher, clock, uuids)

    async def execute(self, command: CreateChannelCommand) -> CreateChannelResultDTO:
        """Применяет команду через агрегат и возвращает результат без выполнения commit."""
        try:
            definition = self._registry.get(command.kind)
        except ChannelNotFoundError:
            raise InvalidChannelError("Unknown channel platform.") from None
        require_writable(definition, command.config_version)
        self._validator.validate(definition, command.connection_settings)
        channel = Channel.create(
            channel_id=ChannelIdVO.from_value(self._uuids.new()),
            name=command.name,
            kind=definition.kind,
            config_version=definition.config_version,
            settings=seal_settings(
                definition, command.connection_settings, self._cipher
            ),
            is_active=command.is_active,
            actor_id=EntityIdVO.from_value(command.actor_id),
            now=self._clock.now(),
        )
        await self._repository.add(channel)
        if (
            self._imports is not None
            and channel.is_active
            and channel.kind in (ChannelKind.PROM, ChannelKind.WOOCOMMERCE)
        ):
            await self._imports.start(
                channel=channel, tenant_id=command.tenant_id, now=self._clock.now()
            )
        return CreateChannelResultDTO.from_channel(channel, definition.type)
