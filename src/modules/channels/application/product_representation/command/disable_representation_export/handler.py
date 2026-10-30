from src.modules.channels.application.product_representation.command.disable_representation_export.command import (
    DisableRepresentationExportCommand,
)
from src.modules.channels.application.product_representation.command.disable_representation_export.dto import (
    DisableRepresentationExportResultDTO,
)
from src.modules.channels.application.product_representation.service.writes import (
    RepresentationWrites,
)


class DisableRepresentationExportHandler:
    """Выполняет отдельное намерение disable_representation_export на портах общего UoW."""

    def __init__(self, writes: RepresentationWrites) -> None:
        """Получает координатор доменных изменений без доступа к SQL."""
        self._writes = writes

    async def execute(
        self, command: DisableRepresentationExportCommand
    ) -> DisableRepresentationExportResultDTO:
        """Возвращает собственный результат после выполнения доменной операции."""
        context = await self._writes.disable(
            tenant_id=command.tenant_id,
            channel_id=command.channel_id,
            group_id=command.group_id,
            actor_id=command.actor_id,
            expected_revision=command.expected_revision,
            expected_binding_revision=command.expected_binding_revision,
            expected_config_revision=command.expected_config_revision,
        )
        return DisableRepresentationExportResultDTO(
            state=context.state,
            binding_revision=context.binding.revision,
            config_revision=context.channel.config_revision,
            locales=context.locales,
            items=context.binding.items,
        )
