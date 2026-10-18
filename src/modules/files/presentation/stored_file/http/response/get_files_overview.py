from pydantic import BaseModel
from src.modules.files.application.stored_file.file_category import FileCategory
from src.modules.files.application.stored_file.query.get_files_overview.dto import (
    FilesOverviewCategoryDTO,
    GetFilesOverviewResultDTO,
)


class FilesOverviewCategoryResponse(BaseModel):
    """HTTP-счётчики активных файлов одной категории сводки."""

    category: FileCategory
    files_count: int
    size_bytes: int

    @classmethod
    def from_dto(cls, dto: FilesOverviewCategoryDTO) -> "FilesOverviewCategoryResponse":
        """Явно переносит значения категории сводки."""
        return cls(
            category=dto.category,
            files_count=dto.files_count,
            size_bytes=dto.size_bytes,
        )


class GetFilesOverviewResponse(BaseModel):
    """HTTP-сводка выбранных дисков без фиктивной квоты и storage secrets."""

    active_count: int
    active_size_bytes: int
    trashed_count: int
    trashed_size_bytes: int
    pending_purge_count: int
    pending_purge_size_bytes: int
    categories: list[FilesOverviewCategoryResponse]

    @classmethod
    def from_dto(cls, dto: GetFilesOverviewResultDTO) -> "GetFilesOverviewResponse":
        """Создаёт отдельный HTTP-контракт из специализированного результата."""
        return cls(
            active_count=dto.active_count,
            active_size_bytes=dto.active_size_bytes,
            trashed_count=dto.trashed_count,
            trashed_size_bytes=dto.trashed_size_bytes,
            pending_purge_count=dto.pending_purge_count,
            pending_purge_size_bytes=dto.pending_purge_size_bytes,
            categories=[
                FilesOverviewCategoryResponse.from_dto(item) for item in dto.categories
            ],
        )
