from src.modules.channels.application.content_media.command.revoke_media_access.command import (
    RevokeMediaAccessCommand,
)
from src.modules.channels.application.content_media.command.revoke_media_access.dto import (
    RevokeMediaAccessResultDTO,
)
from src.modules.channels.application.content_media.service.transfers import (
    MediaTransfers,
)


class RevokeMediaAccessHandler:
    """Координирует отдельный сценарий revoke_media_access."""

    def __init__(self, service: MediaTransfers) -> None:
        """Получает сервис общего UoW."""
        self._service = service

    async def execute(
        self, command: RevokeMediaAccessCommand
    ) -> RevokeMediaAccessResultDTO:
        """Выполняет revoke_media_access через конкретные порты."""
        result = await self._service.revoke(
            channel_id=command.channel_id,
            media_id=command.media_id,
            expected_revision=command.expected_revision,
        )
        return RevokeMediaAccessResultDTO(media_id=command.media_id, revision=result)
