from uuid import UUID

from src.modules.feed_builder.application.export_state.port.file_content import (
    ExportFileContentDTO,
    FeedFileMissingError,
    FeedFileStorageError,
)
from src.modules.files.application.port.storage import StorageUnavailableError
from src.modules.files.application.stored_file.query.get_file_content.handler import (
    GetFileContentHandler,
)
from src.modules.files.application.stored_file.query.get_file_content.query import (
    GetFileContentQuery,
)
from src.modules.files.domain.error import FileNotFoundError


class FilesFeedExportContent:
    """Адаптирует чтение Files к публичному экспорту."""

    def __init__(self, content: GetFileContentHandler) -> None:
        """Получает публичный сценарий Files на tenant-сессии."""
        self._content = content

    async def open(self, tenant_id: UUID, file_id: UUID) -> ExportFileContentDTO:
        """Открывает поток без передачи внутренних моделей Files."""
        try:
            result = await self._content.execute(
                GetFileContentQuery(tenant_id, file_id)
            )
        except FileNotFoundError as exc:
            raise FeedFileMissingError from exc
        except StorageUnavailableError as exc:
            raise FeedFileStorageError from exc
        return ExportFileContentDTO(result.size_bytes, result.stream)
