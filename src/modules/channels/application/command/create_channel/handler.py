from collections.abc import Callable
from datetime import datetime
from uuid import UUID

from src.modules.channels.application.command.create_channel.command import (
    CreateChannelCommand,
)
from src.modules.channels.application.command.create_channel.dto import (
    CreateChannelDTO,
)
from src.modules.channels.application.port.jobs import (
    VerificationJobs,
    VerificationJob,
)
from src.modules.channels.application.port.platform import PlatformRegistry
from src.modules.channels.application.port.settings_catalog import (
    ChannelSettingsCatalog,
)
from src.modules.channels.domain.aggregate import Channel
from src.modules.channels.domain.connection import Connection
from src.modules.channels.domain.repository import ChannelRepositoryProtocol
from src.modules.channels.domain.value_object.channel_name import ChannelNameVO
from src.modules.shared.application.crypto.cipher import Cipher
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


class CreateChannelHandler:
    """Создаёт полный агрегат и задание в одном внешнем UoW."""

    def __init__(
        self,
        repository: ChannelRepositoryProtocol,
        jobs: VerificationJobs,
        platforms: PlatformRegistry,
        cipher: Cipher,
        clock: Callable[[], datetime],
        uuid: Callable[[], UUID],
        *,
        settings_catalog: ChannelSettingsCatalog,
    ) -> None:
        """Принимает порты одной транзакции и фабрики значений."""
        (
            self.repository,
            self.jobs,
            self.platforms,
            self.cipher,
            self.clock,
            self.uuid,
        ) = (repository, jobs, platforms, cipher, clock, uuid)
        self.settings_catalog = settings_catalog

    async def execute(self, command: CreateChannelCommand) -> CreateChannelDTO:
        """Валидирует локальные модели, шифрует секрет и планирует проверку."""
        validated = self.platforms.get(command.platform_kind).validate(
            command.config, command.credentials
        )
        await self.settings_catalog.ensure_available(
            currency=validated.currency, locales=validated.locales
        )
        assert validated.credentials is not None
        now, job_id = self.clock(), self.uuid()
        connection = Connection.create(
            connection_id=EntityIdVO.from_value(self.uuid()),
            config=validated.config,
            encrypted_credentials=self.cipher.encrypt(validated.credentials),
            job_id=EntityIdVO.from_value(job_id),
        )
        channel = Channel.create(
            channel_id=EntityIdVO.from_value(self.uuid()),
            name=ChannelNameVO(command.name),
            platform_kind=command.platform_kind,
            connection=connection,
            actor_id=EntityIdVO.from_value(command.actor_id),
            now=now,
        )
        await self.repository.save(channel)
        await self.jobs.schedule(
            VerificationJob(
                command.tenant_id, channel.id.uuid, connection.id.uuid, job_id, 1
            ),
            now,
        )
        return CreateChannelDTO(channel.id.uuid, channel.revision, job_id)
