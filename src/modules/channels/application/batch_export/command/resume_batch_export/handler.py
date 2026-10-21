from src.modules.channels.application.batch_export.command.resume_batch_export.dto import (
    ResumeBatchExportResultDTO,
)
from uuid import uuid5
from src.modules.channels.application.batch_export.access import BatchExportAccess
from src.modules.channels.application.batch_export.command.resume_batch_export.command import (
    ResumeBatchExportCommand,
)
from src.modules.channels.domain.batch_export.aggregate import ACTIVE
from src.modules.channels.domain.error import ChannelsConflictError


class ResumeBatchExportHandler:
    """Восстанавливает durable выполнение без повторной записи после принятого POST."""

    def __init__(self, access: BatchExportAccess) -> None:
        """Принимает порты без сетевых клиентов."""
        self.a = access

    async def execute(
        self, command: ResumeBatchExportCommand
    ) -> ResumeBatchExportResultDTO:
        """Устаревший шаг становится no-op по sequence; unknown допускает только чтение."""
        a = self.a
        run, _ = await a.locked(command.run_id)
        if run.status not in ACTIVE:
            raise ChannelsConflictError("batch_export_already_finished")
        if run.status != "unknown" and await a.jobs.is_recoverable(
            command.tenant_id, uuid5(run.id, "batch:" + str(run.sequence))
        ):
            return ResumeBatchExportResultDTO(run.id)
        if run.status == "unknown":
            run.reconcile(a.clock.now())
            await a.runs.reopen_verification(run.id)
        else:
            # При submitting следующий шаг только фиксирует неопределённость.
            run.touch(a.clock.now())
        await a.runs.save(run)
        await a.jobs.batch_export(
            command.tenant_id, run.id, run.sequence, a.clock.now()
        )
        return ResumeBatchExportResultDTO(run.id)
