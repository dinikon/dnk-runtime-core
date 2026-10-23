from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class FindUsedImageFilesResultDTO:
    """Возвращает файлы, которые нельзя очищать как временные."""

    file_ids: tuple[UUID, ...]
