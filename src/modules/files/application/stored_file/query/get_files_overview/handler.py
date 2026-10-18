from dataclasses import replace
from src.modules.files.application.stored_file.query.get_files_overview.query import (
    GetFilesOverviewQuery,
)
from src.modules.files.application.stored_file.query.get_files_overview.dto import (
    GetFilesOverviewResultDTO,
)
from src.modules.files.application.stored_file.port.query_repository import (
    StoredFileQueryRepositoryProtocol,
)
from src.modules.files.application.stored_file.read_scope import (
    ensure_selected_buckets,
    validate_bucket_ids,
)


class GetFilesOverviewHandler:
    """Получает общую сводку дисков, независимую от поиска и категории таблицы."""

    def __init__(self, repository: StoredFileQueryRepositoryProtocol) -> None:
        """Принимает порт проекций текущего tenant."""
        self._repository = repository

    async def execute(self, query: GetFilesOverviewQuery) -> GetFilesOverviewResultDTO:
        """Проверяет выбранные диски и возвращает специализированную сводку."""
        validate_bucket_ids(query.bucket_ids)
        normalized = replace(query, bucket_ids=tuple(dict.fromkeys(query.bucket_ids)))
        await ensure_selected_buckets(self._repository, normalized.bucket_ids)
        return await self._repository.get_files_overview(normalized)
