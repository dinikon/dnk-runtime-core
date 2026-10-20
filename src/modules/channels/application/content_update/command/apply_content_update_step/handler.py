from src.modules.shared.domain.time.clock_port import ClockPort
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.channels.application.content_update.command.apply_content_update_step.command import (
    ApplyContentUpdateStepCommand,
)
from src.modules.channels.application.content_update.command.apply_content_update_step.dto import (
    ApplyContentUpdateStepResultDTO,
)
from src.modules.channels.application.content_update.access import ContentUpdateAccess
from src.modules.channels.application.content_update.port.jobs import ContentUpdateJobs
from src.modules.channels.domain.error import ChannelsConflictError


class ApplyContentUpdateStepHandler:
    """Сохраняет факт доставки и следующий job атомарно, без вызова других handlers."""

    def __init__(
        self, access: ContentUpdateAccess, jobs: ContentUpdateJobs, clock: ClockPort
    ) -> None:
        """Получает порты одной короткой tenant-транзакции."""
        self.access, self.jobs, self.clock = access, jobs, clock

    async def execute(
        self, command: ApplyContentUpdateStepCommand
    ) -> ApplyContentUpdateStepResultDTO:
        """Не считает принятие запроса успешным обновлением и сохраняет неопределённость."""
        run, channel = await self.access.locked(command.run_id)
        item = run.current(command.sequence)
        if item is None or item.publication_id.uuid != command.publication_id:
            return ApplyContentUpdateStepResultDTO(False)
        if channel.require_connection().generation != run.generation:
            run.invalidate("connection_generation_changed")
        else:
            run.apply_step(
                command.sequence,
                EntityIdVO(command.publication_id),
                command.mode,
                command.observed,
                command.issues,
                command.error_code,
                command.uncertain,
            )
            pending = run.advance()
            if pending:
                await self.jobs.content_update(
                    command.tenant_id, run.id.uuid, run.sequence, self.clock.now()
                )
        await self.access.runs.save(run)
        return ApplyContentUpdateStepResultDTO(True)
