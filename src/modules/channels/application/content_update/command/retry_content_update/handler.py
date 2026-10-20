from uuid import uuid5
from src.modules.shared.domain.time.clock_port import ClockPort
from src.modules.channels.application.content_update.command.retry_content_update.command import (
    RetryContentUpdateCommand,
)
from src.modules.channels.application.content_update.command.retry_content_update.dto import (
    RetryContentUpdateResultDTO,
)
from src.modules.channels.application.content_update.access import ContentUpdateAccess

from src.modules.channels.application.content_update.port.jobs import ContentUpdateJobs
from src.modules.channels.application.port.jobs import ChannelsJobsProtocol
from src.modules.channels.domain.error import ChannelsConflictError


class RetryContentUpdateHandler:
    """Восстанавливает потерянный job или явно повторяет только контрольное чтение."""

    def __init__(
        self,
        access: ContentUpdateAccess,
        jobs: ContentUpdateJobs,
        status: ChannelsJobsProtocol,
        clock: ClockPort,
    ) -> None:
        """Принимает public jobs-порт для определения прерванного шага."""
        self.access, self.jobs, self.status, self.clock = access, jobs, status, clock

    async def execute(
        self, command: RetryContentUpdateCommand
    ) -> RetryContentUpdateResultDTO:
        """Никогда не повторяет отправку с неизвестным результатом автоматически."""
        run, channel = await self.access.locked(command.run_id, command.actor_id)
        run.ensure_revision(command.expected_revision)
        await self.access.validate(
            run, channel, command.tenant_id, sending=False, check_content=False
        )
        if run.status in ("preparing", "queued", "running"):
            job_id = uuid5(run.id.uuid, "content:" + str(run.sequence))
            if await self.status.is_recoverable(command.tenant_id, job_id):
                raise ChannelsConflictError("content_update_in_progress")
            run.recover()
        else:
            run.retry(command.expected_revision)
        await self.access.runs.save(run)
        await self.jobs.content_update(
            command.tenant_id, run.id.uuid, run.sequence, self.clock.now()
        )
        return RetryContentUpdateResultDTO(run.id.uuid)
