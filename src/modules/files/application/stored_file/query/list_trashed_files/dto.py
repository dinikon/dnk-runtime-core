from dataclasses import dataclass
from datetime import datetime
from uuid import UUID
from src.modules.files.application.stored_file.file_category import FileCategory


@dataclass(frozen=True, slots=True)
class ListTrashedFilesItemDTO:
    """Строка корзины с датами удаления без объектов хранения."""

    file_id: UUID
    bucket_id: UUID
    bucket_name: str
    provider_id: UUID
    provider_name: str
    name: str
    content_type: str
    category: FileCategory
    size_bytes: int
    created_at: datetime
    status: str
    deleted_at: datetime
    purge_after: datetime
    purge_requested_at: datetime | None


@dataclass(frozen=True, slots=True)
class ListTrashedFilesResultDTO:
    """Страница корзины и общее число результатов того же снимка."""

    items: tuple[ListTrashedFilesItemDTO, ...]
    total: int
    page: int
    page_size: int
