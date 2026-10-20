from src.modules.shared.domain.time.clock_port import ClockPort
from src.modules.channels.application.content_update.command.confirm_content_update.command import (
    ConfirmContentUpdateCommand,
)
from src.modules.channels.application.content_update.command.confirm_content_update.dto import (
    ConfirmContentUpdateResultDTO,
)
from src.modules.channels.application.content_update.access import ContentUpdateAccess
from src.modules.channels.application.content_update.port.jobs import ContentUpdateJobs
from src.modules.channels.domain.error import ChannelsConflictError


class ConfirmContentUpdateHandler:
    """Подтверждает ровно показанный снимок и атомарно ставит отправку."""

    def __init__(
        self, access: ContentUpdateAccess, jobs: ContentUpdateJobs, clock: ClockPort
    ) -> None:
        """Принимает порты общей транзакции."""
        self.access, self.jobs, self.clock = access, jobs, clock

    async def execute(
        self, command: ConfirmContentUpdateCommand
    ) -> ConfirmContentUpdateResultDTO:
        """Проверяет replay до текущего источника; новый intent проверяет все revisions."""
        run, channel = await self.access.locked(command.run_id, command.actor_id)
        if run.confirmed_at is not None:
            run.confirm(
                command.expected_revision, command.preview_hash, self.clock.now()
            )
            return ConfirmContentUpdateResultDTO(run.id.uuid)
        await self.access.validate(
            run, channel, command.tenant_id, sending=True, check_content=True
        )
        await self.access.runs.lock_scope(channel.id)
        if await self.access.runs.busy(run):
            raise ChannelsConflictError("content_update_target_busy")
        run.confirm(command.expected_revision, command.preview_hash, self.clock.now())
        await self.access.runs.save(run)
        await self.jobs.content_update(
            command.tenant_id, run.id.uuid, run.sequence, self.clock.now()
        )
        return ConfirmContentUpdateResultDTO(run.id.uuid)
