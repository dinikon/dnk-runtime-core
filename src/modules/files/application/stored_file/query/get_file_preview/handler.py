from src.modules.files.application.port.query_repository import (
    StorageQueryRepositoryProtocol,
)
from src.modules.files.application.port.storage import StorageResolverProtocol
from src.modules.files.application.stored_file.error import UnsupportedFilePreviewError
from src.modules.files.application.stored_file.query.get_file_preview.dto import (
    GetFilePreviewResultDTO,
)
from src.modules.files.application.stored_file.query.get_file_preview.query import (
    GetFilePreviewQuery,
)
from src.modules.files.domain.error import FileNotFoundError

PREVIEW_MEDIA_TYPES = frozenset(
    {
        "image/png",
        "image/jpeg",
        "image/gif",
        "image/webp",
        "image/avif",
        "image/bmp",
        "application/pdf",
        "audio/mpeg",
        "audio/mp4",
        "audio/ogg",
        "audio/webm",
        "audio/wav",
        "audio/x-wav",
        "video/mp4",
        "video/webm",
        "video/ogg",
    }
)
PREVIEW_TEXT_TYPES = frozenset(
    {"text/plain", "text/csv", "text/markdown", "application/json"}
)


class GetFilePreviewHandler:
    """Открывает поддержанный готовый файл после подтверждения ownership хранилища."""

    def __init__(
        self,
        repository: StorageQueryRepositoryProtocol,
        storage: StorageResolverProtocol,
    ) -> None:
        """Принимает порты проекций и storage без HTTP, SDK и управления транзакцией."""
        self._repository, self._storage = repository, storage

    async def execute(self, query: GetFilePreviewQuery) -> GetFilePreviewResultDTO:
        """Возвращает управляемый поток; неподдержанные форматы не открывает."""
        file = await self._repository.content_location(query.tenant_id, query.file_id)
        if file is None:
            raise FileNotFoundError("File is not available.")
        mime = file.content_type.partition(";")[0].strip().lower()
        if mime in PREVIEW_TEXT_TYPES:
            # Текстовые данные показываются как текст, без выполнения разметки.
            media_type = "text/plain; charset=utf-8"
        elif mime in PREVIEW_MEDIA_TYPES:
            media_type = mime
        else:
            raise UnsupportedFilePreviewError("File format does not support preview.")
        adapter = self._storage.resolve(file.location)
        if not await adapter.exists_owned(file.location, file.key):
            raise FileNotFoundError("File object was not found.")
        stream = await adapter.open(file.location, file.key)
        return GetFilePreviewResultDTO(
            query.file_id, file.name, media_type, file.size_bytes, stream
        )
