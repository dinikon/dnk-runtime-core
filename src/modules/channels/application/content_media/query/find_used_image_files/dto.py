from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class FindUsedImageFilesResultDTO:
    """Передаёт только ID, которые нельзя удалять."""

    file_ids: tuple[UUID, ...]
