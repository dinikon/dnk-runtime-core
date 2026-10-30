from src.modules.channels.application.content_media.command.record_media_transfer_result.command import (
    RecordMediaTransferResultCommand,
)
from src.modules.channels.application.content_media.command.record_media_transfer_result.dto import (
    RecordMediaTransferResultResultDTO,
)
from src.modules.channels.application.content_media.service.transfers import (
    MediaTransfers,
)


class RecordMediaTransferResultHandler:
    """Координирует отдельный сценарий record_media_transfer_result."""

    def __init__(self, service: MediaTransfers) -> None:
        """Получает сервис общего UoW."""
        self._service = service

    async def execute(
        self, command: RecordMediaTransferResultCommand
    ) -> RecordMediaTransferResultResultDTO:
        """Выполняет record_media_transfer_result через конкретные порты."""
        result = await self._service.record(
            channel_id=command.channel_id,
            config_revision=command.config_revision,
            identity_namespace=command.identity_namespace,
            identity_key=command.identity_key,
            operation_id=command.operation_id,
            media_id=command.media_id,
            expected_revision=command.expected_revision,
            remote_id=command.remote_id,
            error=command.error,
            uncertain=command.uncertain,
        )
        return RecordMediaTransferResultResultDTO(applied=result)
