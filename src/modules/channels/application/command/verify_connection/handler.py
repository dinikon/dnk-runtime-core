from collections.abc import Callable
from datetime import datetime
from uuid import UUID

from src.modules.channels.application.command.verify_connection.command import (
    VerifyConnectionCommand,
)
from src.modules.channels.application.command.verify_connection.dto import (
    VerifyConnectionDTO,
)
from src.modules.channels.application.port.jobs import (
    VerificationJobs,
    VerificationJob,
)
from src.modules.channels.domain.enum.verification_status import (
    VerificationStatus,
)
from src.modules.channels.domain.error import ChannelNotFoundError
from src.modules.channels.domain.repository import ChannelRepositoryProtocol
from src.modules.shared.application.crypto.cipher import Cipher
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


class VerifyConnectionHandler:
    """Планирует проверку текущей сохранённой конфигурации."""

    def __init__(
        self,
        repository: ChannelRepositoryProtocol,
        jobs: VerificationJobs,
        cipher: Cipher,
        clock: Callable[[], datetime],
        uuid: Callable[[], UUID],
    ) -> None:
        """Принимает зависимости внешнего UoW."""
        self.repository, self.jobs, self.cipher, self.clock, self.uuid = (
            repository,
            jobs,
            cipher,
            clock,
            uuid,
        )

    async def execute(self, command: VerifyConnectionCommand) -> VerifyConnectionDTO:
        """Переиспользует активное задание либо создаёт новое поколение."""
        channel = await self.repository.get(
            EntityIdVO.from_value(command.channel_id), for_update=True
        )
        if channel is None:
            raise ChannelNotFoundError("Канал не найден.")
        c = channel.connection
        if (
            c.verification.status is VerificationStatus.PENDING
            and await self.jobs.active(command.tenant_id, c.verification.job_id.uuid)
        ):
            return VerifyConnectionDTO(
                channel.id.uuid, channel.revision, c.verification.job_id.uuid
            )
        self.cipher.require_configured()
        now, job_id = self.clock(), self.uuid()
        channel.request_verification(
            job_id=EntityIdVO.from_value(job_id),
            actor_id=EntityIdVO.from_value(command.actor_id),
            now=now,
        )
        await self.repository.save(channel)
        await self.jobs.schedule(
            VerificationJob(
                command.tenant_id, channel.id.uuid, c.id.uuid, job_id, c.config_revision
            ),
            now,
        )
        return VerifyConnectionDTO(channel.id.uuid, channel.revision, job_id)
