from src.modules.channels.application.batch_export.access import BatchExportAccess
from src.modules.channels.application.batch_export.command.prepare_export_artifact_page.command import (
    PrepareExportArtifactPageCommand,
)
from src.modules.channels.application.batch_export.command.prepare_export_artifact_page.dto import (
    PrepareExportArtifactPageResultDTO,
)


class PrepareExportArtifactPageHandler:
    """Проверяет допуск текущего процесса перед чтением ограниченной части файла."""

    def __init__(self, access: BatchExportAccess) -> None:
        """Принимает порты владельцев без SQL и сетевых клиентов."""
        self.a = access

    async def execute(
        self, command: PrepareExportArtifactPageCommand
    ) -> PrepareExportArtifactPageResultDTO | None:
        """Не позволяет сборщику продолжать отозванный или устаревший шаг."""
        run, channel = await self.a.locked(command.run_id)
        if run.status != "building" or run.sequence != command.sequence:
            return None
        channel.ensure_outbound(run.generation)
        return PrepareExportArtifactPageResultDTO(
            await self.a.runs.page(run.id, "ready", command.after)
        )
