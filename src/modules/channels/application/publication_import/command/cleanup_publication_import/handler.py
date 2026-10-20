from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.channels.application.publication_import.command.cleanup_publication_import.command import (
    CleanupPublicationImportCommand,
)
from src.modules.channels.application.publication_import.command.cleanup_publication_import.dto import (
    CleanupPublicationImportResultDTO,
)
from src.modules.channels.application.publication_import.access import (
    PublicationImportAccess,
)
from src.modules.channels.application.publication_import.port.files import (
    PublicationImportFilesPort,
)
from src.modules.channels.domain.publication_import.repository import (
    PublicationImportRepositoryProtocol,
)
from src.modules.shared.domain.time.clock_port import ClockPort


class CleanupPublicationImportHandler:
    """Освобождает временные файлы, сериализуясь с подтверждением создания товара."""

    def __init__(
        self,
        access: PublicationImportAccess,
        imports: PublicationImportRepositoryProtocol,
        files: PublicationImportFilesPort,
        clock: ClockPort,
    ) -> None:
        """Получает публичный порт файлов и текущий tenant UoW."""
        self.access, self.imports, self.files, self.clock = (
            access,
            imports,
            files,
            clock,
        )

    async def execute(
        self, command: CleanupPublicationImportCommand
    ) -> CleanupPublicationImportResultDTO:
        """Не удаляет принятые товаром файлы и проверяет иные использования через владельца."""
        preparation, source = await self.access.locked(command.preparation_id)
        now = self.clock.now()
        if (
            preparation.status not in ("cancelled", "consumed")
            and now < preparation.expires_at
        ):
            return CleanupPublicationImportResultDTO(0)
        if now >= preparation.expires_at:
            preparation.expire(now)
        keys = tuple(
            key
            for key, value in preparation.media.items()
            if value.file_id and key not in preparation.used_image_ids
        )
        await self.files.release(
            command.tenant_id,
            preparation.actor_id.uuid,
            tuple(preparation.media[key].file_id.uuid for key in keys),
        )
        preparation.cleaned(keys)
        await self.imports.save(preparation)
        return CleanupPublicationImportResultDTO(len(keys))
