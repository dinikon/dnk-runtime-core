from src.modules.channels.application.product_representation.command.enable_representation_export.command import (
    EnableRepresentationExportCommand,
)
from src.modules.channels.application.product_representation.command.enable_representation_export.dto import (
    EnableRepresentationExportResultDTO,
)
from src.modules.channels.application.product_representation.service.writes import (
    RepresentationWrites,
)


class EnableRepresentationExportHandler:
    """Выполняет отдельное намерение enable_representation_export на портах общего UoW."""

    def __init__(self, writes: RepresentationWrites) -> None:
        """Получает координатор доменных изменений без доступа к SQL."""
        self._writes = writes

    async def execute(
        self, command: EnableRepresentationExportCommand
    ) -> EnableRepresentationExportResultDTO:
        """Возвращает собственный результат после выполнения доменной операции."""
        context = await self._writes.enable(
            tenant_id=command.tenant_id,
            channel_id=command.channel_id,
            group_id=command.group_id,
            actor_id=command.actor_id,
            expected_revision=command.expected_revision,
            expected_binding_revision=command.expected_binding_revision,
            expected_config_revision=command.expected_config_revision,
        )
        return EnableRepresentationExportResultDTO(
            state=context.state,
            binding_revision=context.binding.revision,
            config_revision=context.channel.config_revision,
            locales=context.locales,
            items=context.binding.items,
        )
