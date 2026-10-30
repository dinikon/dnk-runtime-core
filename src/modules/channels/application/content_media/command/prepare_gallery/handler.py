from src.modules.channels.application.content_media.command.prepare_gallery.command import (
    PrepareGalleryCommand,
)
from src.modules.channels.application.content_media.command.prepare_gallery.dto import (
    PrepareGalleryResultDTO,
)
from src.modules.channels.application.content_media.service.galleries import (
    MediaGalleries,
)
from src.modules.channels.application.content_media.port.access import (
    MediaAuthorizationPort,
)


class PrepareGalleryHandler:
    """Координирует отдельный сценарий prepare_gallery."""

    def __init__(
        self, service: MediaGalleries, authorization: MediaAuthorizationPort
    ) -> None:
        """Получает сервис общего UoW и права инициатора."""
        self._service = service
        self._authorization = authorization

    async def execute(self, command: PrepareGalleryCommand) -> PrepareGalleryResultDTO:
        """Выполняет prepare_gallery через конкретные порты."""
        result = await self._service.prepare(
            tenant_id=command.tenant_id,
            channel_id=command.channel_id,
            group_id=command.group_id,
            expected_revision=command.expected_revision,
            expected_binding_revision=command.expected_binding_revision,
            expected_config_revision=command.expected_config_revision,
            authorization=self._authorization,
        )
        return PrepareGalleryResultDTO(galleries=result)
