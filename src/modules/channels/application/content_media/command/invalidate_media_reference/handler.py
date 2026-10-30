from src.modules.channels.application.content_media.command.invalidate_media_reference.command import (
    InvalidateMediaReferenceCommand,
)
from src.modules.channels.application.content_media.command.invalidate_media_reference.dto import (
    InvalidateMediaReferenceResultDTO,
)
from src.modules.channels.application.content_media.service.transfers import (
    MediaTransfers,
)


class InvalidateMediaReferenceHandler:
    """Сбрасывает только проверенный устаревший ID, сохраняя URL и файл."""

    def __init__(self, transfers: MediaTransfers) -> None:
        """Принимает write-координацию общей сессии исполнителя."""
        self._transfers = transfers

    async def execute(
        self, command: InvalidateMediaReferenceCommand
    ) -> InvalidateMediaReferenceResultDTO:
        """Применяет доменный переход после блокировки Channel и media."""
        media = await self._transfers.lock(
            channel_id=command.channel_id, media_id=command.media_id
        )
        media.invalidate_remote(
            expected_revision=command.expected_revision, now=self._transfers.clock.now()
        )
        await self._transfers.media.save(media)
        return InvalidateMediaReferenceResultDTO(media.id.uuid, media.revision)
