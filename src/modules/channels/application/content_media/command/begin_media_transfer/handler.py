from src.modules.channels.application.content_media.command.begin_media_transfer.command import (
    BeginMediaTransferCommand,
)
from src.modules.channels.application.content_media.command.begin_media_transfer.dto import (
    BeginMediaTransferResultDTO,
)
from src.modules.channels.application.content_media.service.transfers import (
    MediaTransfers,
)


class BeginMediaTransferHandler:
    """Координирует отдельный сценарий begin_media_transfer."""

    def __init__(self, service: MediaTransfers) -> None:
        """Получает сервис общего UoW."""
        self._service = service

    async def execute(
        self, command: BeginMediaTransferCommand
    ) -> BeginMediaTransferResultDTO:
        """Выполняет begin_media_transfer через конкретные порты."""
        result = await self._service.begin(
            tenant_id=command.tenant_id,
            channel_id=command.channel_id,
            group_id=command.group_id,
            expected_revision=command.expected_revision,
            expected_binding_revision=command.expected_binding_revision,
            expected_config_revision=command.expected_config_revision,
            media_revisions=command.media_revisions,
            operation_id=command.operation_id,
        )
        return BeginMediaTransferResultDTO(media_ids=result)
