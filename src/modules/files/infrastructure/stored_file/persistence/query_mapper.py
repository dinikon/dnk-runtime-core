from src.modules.files.application.stored_file.command.cleanup_expired_trash.dto import (
    CleanupExpiredTrashCandidateDTO,
    CleanupExpiredTrashBacklogDTO,
)
from collections.abc import Mapping, Sequence
from src.modules.files.application.stored_file.command.empty_trash.dto import (
    EmptyTrashCandidateDTO,
)
from typing import Any

from src.modules.files.application.stored_file.file_category import FileCategory
from src.modules.files.application.stored_file.port.query_repository import (
    FileReadBucketDTO,
)
from src.modules.files.application.stored_file.query.list_files.dto import (
    ListFilesItemDTO,
)
from src.modules.files.application.stored_file.query.list_trashed_files.dto import (
    ListTrashedFilesItemDTO,
)
from src.modules.files.application.stored_file.query.get_files_overview.dto import (
    FilesOverviewCategoryDTO,
    GetFilesOverviewResultDTO,
)


class StoredFileQueryMapper:
    """Преобразует SQL-проекции в конкретные DTO без I/O и правил агрегатов."""

    @staticmethod
    def to_empty_trash_candidate(row: Mapping[str, Any]) -> EmptyTrashCandidateDTO:
        """Преобразует ID ручной очистки в контракт отдельного сценария."""
        return EmptyTrashCandidateDTO(file_id=row["id"])

    @staticmethod
    def to_cleanup_backlog(row: Mapping[str, Any]) -> CleanupExpiredTrashBacklogDTO:
        """Преобразует один агрегированный снимок в контракт метрик очистки."""
        return CleanupExpiredTrashBacklogDTO(
            expired_count=row["expired_count"],
            expired_size_bytes=int(row["expired_size_bytes"]),
            oldest_purge_after=row["oldest_purge_after"],
            pending_count=row["pending_count"],
            pending_size_bytes=int(row["pending_size_bytes"]),
        )

    @staticmethod
    def to_cleanup_candidate(row: Mapping[str, Any]) -> CleanupExpiredTrashCandidateDTO:
        """Возвращает отдельную проекцию кандидата обслуживания."""
        return CleanupExpiredTrashCandidateDTO(file_id=row["id"])

    @staticmethod
    def to_bucket(row: Mapping[str, Any]) -> FileReadBucketDTO:
        """Преобразует найденный диск в проекцию для проверки фильтра."""
        return FileReadBucketDTO(bucket_id=row["id"], status=row["status"])

    @staticmethod
    def to_list_item(row: Mapping[str, Any]) -> ListFilesItemDTO:
        """Создаёт строку активного списка без данных корзины и storage secrets."""
        return ListFilesItemDTO(
            file_id=row["file_id"],
            bucket_id=row["bucket_id"],
            bucket_name=row["bucket_name"],
            provider_id=row["provider_id"],
            provider_name=row["provider_name"],
            name=row["name"],
            content_type=row["content_type"],
            category=FileCategory(row["category"]),
            size_bytes=row["size_bytes"],
            created_at=row["created_at"],
        )

    @staticmethod
    def to_trash_item(row: Mapping[str, Any]) -> ListTrashedFilesItemDTO:
        """Создаёт собственную строку корзины с состоянием и сроком восстановления."""
        return ListTrashedFilesItemDTO(
            file_id=row["file_id"],
            bucket_id=row["bucket_id"],
            bucket_name=row["bucket_name"],
            provider_id=row["provider_id"],
            provider_name=row["provider_name"],
            name=row["name"],
            content_type=row["content_type"],
            category=FileCategory(row["category"]),
            size_bytes=row["size_bytes"],
            created_at=row["created_at"],
            status=row["status"],
            deleted_at=row["deleted_at"],
            purge_after=row["purge_after"],
            purge_requested_at=row["purge_requested_at"],
        )

    @staticmethod
    def to_overview(rows: Sequence[Mapping[str, Any]]) -> GetFilesOverviewResultDTO:
        """Преобразует четыре строки категорий и повторённые общие счётчики."""
        first = rows[0]
        return GetFilesOverviewResultDTO(
            active_count=first["active_count"],
            active_size_bytes=int(first["active_size_bytes"]),
            trashed_count=first["trashed_count"],
            trashed_size_bytes=int(first["trashed_size_bytes"]),
            pending_purge_count=first["pending_purge_count"],
            pending_purge_size_bytes=int(first["pending_purge_size_bytes"]),
            categories=tuple(
                FilesOverviewCategoryDTO(
                    category=FileCategory(row["category"]),
                    files_count=row["files_count"],
                    size_bytes=int(row["category_size_bytes"]),
                )
                for row in rows
            ),
        )
