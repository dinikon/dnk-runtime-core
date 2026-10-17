from dataclasses import dataclass
from src.modules.files.application.stored_file.file_category import FileCategory


@dataclass(frozen=True, slots=True)
class FilesOverviewCategoryDTO:
    """Количество и суммарный размер активных файлов одной категории."""

    category: FileCategory
    files_count: int
    size_bytes: int


@dataclass(frozen=True, slots=True)
class GetFilesOverviewResultDTO:
    """Сводка реестра выбранных дисков с отдельным итогом ожидающего удаления."""

    active_count: int
    active_size_bytes: int
    trashed_count: int
    trashed_size_bytes: int
    pending_purge_count: int
    pending_purge_size_bytes: int
    categories: tuple[FilesOverviewCategoryDTO, ...]
