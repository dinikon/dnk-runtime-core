from src.modules.files.application.stored_file.command.cleanup_expired_trash.command import (
    CleanupExpiredTrashCommand,
)
from src.modules.files.application.stored_file.command.cleanup_expired_trash.dto import (
    CleanupExpiredTrashCandidateDTO,
    CleanupExpiredTrashBacklogDTO,
)
from datetime import datetime
from dataclasses import dataclass
from typing import Protocol
from uuid import UUID
from src.modules.files.application.stored_file.query.list_files.query import (
    ListFilesQuery,
)
from src.modules.files.application.stored_file.query.list_files.dto import (
    ListFilesResultDTO,
)
from src.modules.files.application.stored_file.query.list_trashed_files.query import (
    ListTrashedFilesQuery,
)
from src.modules.files.application.stored_file.query.list_trashed_files.dto import (
    ListTrashedFilesResultDTO,
)
from src.modules.files.application.stored_file.query.get_files_overview.query import (
    GetFilesOverviewQuery,
)
from src.modules.files.application.stored_file.query.get_files_overview.dto import (
    GetFilesOverviewResultDTO,
)


@dataclass(frozen=True, slots=True)
class FileReadBucketDTO:
    """Проекция существования и доступности явно выбранного диска."""

    bucket_id: UUID
    status: str


class StoredFileQueryRepositoryProtocol(Protocol):
    """Читает специализированные страницы и сводку в выбранной tenant-схеме."""

    async def cleanup_backlog(self, cutoff: datetime) -> CleanupExpiredTrashBacklogDTO:
        """Возвращает агрегированный снимок состояний без загрузки всего реестра."""
        ...

    async def cleanup_candidates(
        self, command: CleanupExpiredTrashCommand
    ) -> tuple[CleanupExpiredTrashCandidateDTO, ...]:
        """Читает не более 100 ID истёкшей корзины и незавершённых удалений по keyset."""
        ...

    async def selected_buckets(
        self, bucket_ids: tuple[UUID, ...]
    ) -> tuple[FileReadBucketDTO, ...]:
        """Возвращает состояния найденных дисков без раскрытия ORM."""
        ...

    async def list_files(self, query: ListFilesQuery) -> ListFilesResultDTO:
        """Возвращает активную страницу и total из одного снимка."""
        ...

    async def list_trashed_files(
        self, query: ListTrashedFilesQuery
    ) -> ListTrashedFilesResultDTO:
        """Возвращает собственную страницу корзины и total из одного снимка."""
        ...

    async def get_files_overview(
        self, query: GetFilesOverviewQuery
    ) -> GetFilesOverviewResultDTO:
        """Возвращает счётчики и размеры состояний и активных категорий."""
        ...
