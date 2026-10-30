from src.modules.channels.application.content_media.command.renew_media_access.command import (
    RenewMediaAccessCommand,
)
from src.modules.channels.application.content_media.command.renew_media_access.dto import (
    RenewMediaAccessResultDTO,
)
from src.modules.channels.application.content_media.service.transfers import (
    MediaTransfers,
)
from src.modules.channels.application.content_media.port.access import (
    MediaAuthorizationPort,
)


class RenewMediaAccessHandler:
    """Координирует отдельный сценарий renew_media_access."""

    def __init__(
        self, service: MediaTransfers, authorization: MediaAuthorizationPort
    ) -> None:
        """Получает сервис общего UoW и права инициатора."""
        self._service = service
        self._authorization = authorization

    async def execute(
        self, command: RenewMediaAccessCommand
    ) -> RenewMediaAccessResultDTO:
        """Выполняет renew_media_access через конкретные порты."""
        result = await self._service.renew(
            channel_id=command.channel_id,
            media_id=command.media_id,
            expected_revision=command.expected_revision,
            authorization=self._authorization,
        )
        return RenewMediaAccessResultDTO(
            media_id=command.media_id, revision=result[0], url=result[1]
        )
