from dataclasses import dataclass
from uuid import UUID
from src.modules.files.application.stored_file.file_category import FileCategory


@dataclass(frozen=True, slots=True)
class ListTrashedFilesQuery:
    """Параметры корзины текущего tenant."""

    tenant_id: UUID
    search: str = ""
    bucket_ids: tuple[UUID, ...] = ()
    category: FileCategory | None = None
    page: int = 1
    page_size: int = 20
