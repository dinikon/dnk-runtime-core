from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class StartPublicationImportResultDTO:
    """Возвращает идентификатор нового или уже активного запуска."""

    run_id: UUID
