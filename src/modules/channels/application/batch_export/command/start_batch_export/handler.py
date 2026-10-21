from src.modules.channels.application.batch_export.access import BatchExportAccess
from src.modules.channels.application.batch_export.service.start import (
    BatchExportStarter,
)
from src.modules.channels.application.batch_export.command.start_batch_export.command import (
    StartBatchExportCommand,
)
from src.modules.channels.application.batch_export.command.start_batch_export.dto import (
    StartBatchExportResultDTO,
)
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


class StartBatchExportHandler:
    """Принимает ручной запуск в транзакции вместе с durable intent."""

    def __init__(self, access: BatchExportAccess) -> None:
        """Принимает специализированные порты без инфраструктуры."""
        self.access = access

    async def execute(
        self, command: StartBatchExportCommand
    ) -> StartBatchExportResultDTO:
        """Не разрешает синхронизацию неявно и не создаёт второй пакет на повторный клик."""
        a = self.access
        channel = await a.channels.get(EntityIdVO(command.channel_id))
        run = await BatchExportStarter(a).start(
            command.tenant_id,
            channel,
            command.run_id,
            command.actor_id,
            "manual",
            a.clock.now(),
            delivery_mode=command.delivery_mode,
        )
        return StartBatchExportResultDTO(run.id)
