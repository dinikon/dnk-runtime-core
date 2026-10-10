from src.modules.files.application.stored_file.query.get_file_content.query import (
    GetFileContentQuery,
)
from src.modules.files.application.stored_file.query.get_file_content.dto import (
    GetFileContentResultDTO,
)
from src.modules.files.application.port.query_repository import (
    StorageQueryRepositoryProtocol,
)
from src.modules.files.application.port.storage import StorageResolverProtocol
from src.modules.files.domain.error import FileNotFoundError


class GetFileContentHandler:
    """Получает поток готового файла через проекцию и порт хранилища."""

    def __init__(
        self,
        repository: StorageQueryRepositoryProtocol,
        storage: StorageResolverProtocol,
    ) -> None:
        """Принимает порты чтения без доступа к SQL или SDK."""
        self._repository, self._storage = repository, storage

    async def execute(self, query: GetFileContentQuery) -> GetFileContentResultDTO:
        """Открывает поток; его закрытие принадлежит вызывающему бизнес-модулю."""
        file = await self._repository.content_location(query.tenant_id, query.file_id)
        if file is None:
            raise FileNotFoundError("File is not available.")
        stream = await self._storage.resolve(file.location).open(
            file.location, file.key
        )
        return GetFileContentResultDTO(
            query.file_id, file.name, file.content_type, file.size_bytes, stream
        )
