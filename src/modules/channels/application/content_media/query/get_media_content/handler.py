from src.modules.channels.application.content_media.query.get_media_content.query import (
    GetMediaContentQuery,
)
from src.modules.channels.application.content_media.query.get_media_content.dto import (
    GetMediaContentResultDTO,
)
from src.modules.channels.application.content_media.service.galleries import (
    MediaGalleries,
)
from src.modules.channels.domain.content_media.error import ContentMediaError


class GetMediaContentHandler:
    """Выдаёт только действующий ресурс и открывает сеть после завершения SQL."""

    def __init__(self, service: MediaGalleries) -> None:
        """Получает read-координацию и общий порт UoW."""
        self._service = service

    async def execute(self, query: GetMediaContentQuery) -> GetMediaContentResultDTO:
        """Проверяет токен, актуальную галерею, Files и затем освобождает транзакцию."""
        row = await self._service.queries.get(query.media_id)
        if (
            row is None
            or row.access_revoked_at is not None
            or not self._service.tokens.matches(query.token, row.access_token_hash)
        ):
            raise ContentMediaError("media_not_found")
        if not await self._service.is_current_use(row):
            raise ContentMediaError("media_not_found")
        files = await self._service.files.describe((row.file_id,))
        file = files[0]
        if file.source_fingerprint != row.source_fingerprint:
            raise ContentMediaError("media_not_found")
        if query.extension is not None and file.extension != query.extension:
            raise ContentMediaError("media_not_found")
        await self._service.uow.commit()
        if query.metadata_only:
            await self._service.files.inspect(files)
            return GetMediaContentResultDTO(
                file.location.content_type, file.location.size_bytes, None
            )
        content = await self._service.files.open(file)
        return GetMediaContentResultDTO(
            content.content_type, content.size_bytes, content.stream
        )
