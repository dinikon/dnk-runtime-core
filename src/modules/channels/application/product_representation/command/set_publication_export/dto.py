from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class SetPublicationExportResultDTO:
    """Возвращает новые версии без изменения связи или каталога."""

    revisions: dict[UUID, int]
