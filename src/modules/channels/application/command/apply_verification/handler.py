from collections.abc import Callable
from datetime import datetime

from src.modules.channels.application.command.apply_verification.command import (
    ApplyVerificationCommand,
)
from src.modules.channels.application.port.jobs import VerificationJobs
from src.modules.channels.domain.repository import ChannelRepositoryProtocol
from src.modules.shared.application.jobs.scheduled_job_deferred import (
    ScheduledJobDeferred,
)
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


class ApplyVerificationHandler:
    """Применяет результат с fencing и закреплением уникального магазина."""

    def __init__(
        self,
        repository: ChannelRepositoryProtocol,
        jobs: VerificationJobs,
        clock: Callable[[], datetime],
    ) -> None:
        """Принимает порты нового короткого UoW worker."""
        self.repository, self.jobs, self.clock = repository, jobs, clock

    async def execute(self, command: ApplyVerificationCommand) -> None:
        """Игнорирует устаревшие результаты, сохраняя единый порядок блокировок."""
        job = command.job
        channel = await self.repository.get(
            EntityIdVO.from_value(job.channel_id), for_update=True
        )
        if (
            channel is None
            or channel.connection.id.uuid != job.connection_id
            or not channel.accepts_result(
                job_id=EntityIdVO.from_value(job.job_id),
                config_revision=job.config_revision,
            )
        ):
            return
        if not await self.jobs.owns(job, command.lock_token, for_update=True):
            return
        error = command.error_code
        identity = command.identity
        if (
            error is None
            and identity is not None
            and channel.can_confirm_identity(identity)
        ):
            if not await self.repository.identity_available(channel.id, identity):
                error = "resource_already_connected"
        channel.apply_verification(
            job_id=EntityIdVO.from_value(job.job_id),
            config_revision=job.config_revision,
            identity=identity,
            error_code=error,
            now=self.clock(),
        )
        await self.repository.save(channel)
        if not await self.jobs.owns(job, command.lock_token):
            raise ScheduledJobDeferred("Verification lease expired before commit.")
