from src.modules.channels.application.publication_import.query.get_publication_import_image.query import (
    GetPublicationImportImageQuery,
)
from src.modules.channels.application.publication_import.query.get_publication_import_image.dto import (
    GetPublicationImportImageResultDTO,
)
from src.modules.channels.application.publication_import.port.query_repository import (
    PublicationImportQueryRepositoryProtocol,
)
from src.modules.channels.application.publication_import.port.files import (
    PublicationImportFilesPort,
)
from src.modules.channels.domain.error import ChannelsNotFoundError
from src.modules.shared.domain.time.clock_port import ClockPort


class GetPublicationImportImageHandler:
    """Разрешает Files content только через состав и владельца подготовки."""

    def __init__(
        self,
        imports: PublicationImportQueryRepositoryProtocol,
        files: PublicationImportFilesPort,
        clock: ClockPort,
    ) -> None:
        """Получает read-проекцию и файловый порт потребителя."""
        self.imports, self.files, self.clock = imports, files, clock

    async def execute(
        self, query: GetPublicationImportImageQuery
    ) -> GetPublicationImportImageResultDTO:
        """Не принимает произвольный file_id от клиента."""
        preparation = await self.imports.get(query.preparation_id)
        if (
            preparation.actor_id != query.actor_id
            or preparation.status in ("cancelled", "expired")
            or self.clock.now() >= preparation.expires_at
        ):
            raise ChannelsNotFoundError("import_preparation_not_found")
        image = next(
            (
                image
                for image in preparation.images
                if image.id == query.image_id and image.file_id
            ),
            None,
        )
        if image is None:
            raise ChannelsNotFoundError("import_image_not_found")
        result = await self.files.content(query.tenant_id, image.file_id)
        return GetPublicationImportImageResultDTO(
            result.content_type, result.size_bytes, result.stream
        )
