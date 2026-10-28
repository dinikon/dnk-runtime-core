from collections.abc import Callable
from datetime import datetime
from uuid import UUID

from src.modules.channels.application.sync_run.service import SyncRuns
from src.modules.channels.application.channel.command.update_channel.command import (
    UpdateChannelCommand,
)
from src.modules.channels.application.channel.command.update_channel.dto import (
    UpdateChannelDTO,
)
from src.modules.channels.application.channel.port.jobs import (
    VerificationJobs,
    VerificationJob,
)
from src.modules.channels.application.port.platform import PlatformRegistry
from src.modules.channels.application.port.settings_catalog import (
    ChannelSettingsCatalog,
)
from src.modules.channels.domain.channel.error import ChannelNotFoundError
from src.modules.channels.domain.channel.repository import ChannelRepositoryProtocol
from src.modules.channels.domain.channel.value_object.channel_name import ChannelNameVO
from src.modules.shared.application.crypto.cipher import Cipher
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


class UpdateChannelHandler:
    """Сохраняет настройки с немедленной заменой credentials."""

    def __init__(
        self,
        repository: ChannelRepositoryProtocol,
        jobs: VerificationJobs,
        platforms: PlatformRegistry,
        cipher: Cipher,
        clock: Callable[[], datetime],
        uuid: Callable[[], UUID],
        *,
        settings_catalog: ChannelSettingsCatalog | None = None,
        sync_runs: SyncRuns | None = None,
    ) -> None:
        """Принимает зависимости внешнего UoW."""
        (
            self.repository,
            self.jobs,
            self.platforms,
            self.cipher,
            self.clock,
            self.uuid,
        ) = (repository, jobs, platforms, cipher, clock, uuid)
        self.settings_catalog = settings_catalog
        self.sync_runs = sync_runs

    async def execute(self, command: UpdateChannelCommand) -> UpdateChannelDTO:
        """Проверяет ревизию до замены секрета и отмены старого задания."""
        channel = await self.repository.get(
            EntityIdVO.from_value(command.channel_id), for_update=True
        )
        if channel is None:
            raise ChannelNotFoundError("Канал не найден.")
        channel.require_revision(command.expected_revision)
        validated = self.platforms.get(channel.platform_kind).validate(
            command.config or channel.connection.config, command.credentials
        )
        current = self.platforms.get(channel.platform_kind).validate(
            channel.connection.config, None
        )
        if self.settings_catalog is not None:
            await self.settings_catalog.ensure_available(
                currency=validated.currency, locales=validated.locales
            )
        encrypted = (
            self.cipher.encrypt(validated.credentials)
            if validated.credentials is not None
            else None
        )
        now, job_id = self.clock(), self.uuid()
        connection_changed = channel.change_settings(
            expected_revision=command.expected_revision,
            name=ChannelNameVO(command.name) if command.name is not None else None,
            config=validated.config if validated.config != current.config else None,
            encrypted_credentials=encrypted,
            job_id=EntityIdVO.from_value(job_id),
            actor_id=EntityIdVO.from_value(command.actor_id),
            now=now,
        )
        if connection_changed:
            if self.sync_runs is not None:
                await self.sync_runs.cancel(
                    channel=channel,
                    tenant_id=command.tenant_id,
                    reason="configuration_changed",
                )
            await self.jobs.cancel(command.tenant_id, channel.id.uuid, now)
        await self.repository.save(channel)
        if connection_changed:
            c = channel.connection
            await self.jobs.schedule(
                VerificationJob(
                    command.tenant_id,
                    channel.id.uuid,
                    c.id.uuid,
                    job_id,
                    c.config_revision,
                ),
                now,
            )
        return UpdateChannelDTO(
            channel.id.uuid,
            channel.revision,
            channel.connection.verification.job_id.uuid,
        )
