from dataclasses import replace
from src.modules.files.application.stored_file.query.list_files.query import (
    ListFilesQuery,
)
from src.modules.files.application.stored_file.query.list_files.dto import (
    ListFilesResultDTO,
)
from src.modules.files.application.stored_file.port.query_repository import (
    StoredFileQueryRepositoryProtocol,
)
from src.modules.files.application.stored_file.read_scope import (
    ensure_selected_buckets,
    validate_file_list_parameters,
)


class ListFilesHandler:
    """Читает активные файлы через порт проекций без восстановления агрегатов."""

    def __init__(self, repository: StoredFileQueryRepositoryProtocol) -> None:
        """Принимает порт чтения на сессии внешнего tenant UoW."""
        self._repository = repository

    async def execute(self, query: ListFilesQuery) -> ListFilesResultDTO:
        """Проверяет параметры и выбранные диски, возвращает страницу своего сценария."""
        validate_file_list_parameters(
            query.search, query.bucket_ids, query.category, query.page, query.page_size
        )
        normalized = replace(
            query,
            search=query.search.strip(),
            bucket_ids=tuple(dict.fromkeys(query.bucket_ids)),
        )
        await ensure_selected_buckets(self._repository, normalized.bucket_ids)
        return await self._repository.list_files(normalized)
