from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class FindUsedImageFilesQuery:
    """Выбирает использование только переданных файлов в Catalog текущего tenant."""

    tenant_id: UUID
    file_ids: tuple[UUID, ...]
