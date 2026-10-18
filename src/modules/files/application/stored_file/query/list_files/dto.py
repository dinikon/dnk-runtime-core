from dataclasses import dataclass
from datetime import datetime
from uuid import UUID
from src.modules.files.application.stored_file.file_category import FileCategory


@dataclass(frozen=True, slots=True)
class ListFilesItemDTO:
    """Строка списка доступных файлов без объектов хранения."""

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


@dataclass(frozen=True, slots=True)
class ListFilesResultDTO:
    """Страница активных файлов и общее число результатов того же снимка."""

    items: tuple[ListFilesItemDTO, ...]
    total: int
    page: int
    page_size: int
