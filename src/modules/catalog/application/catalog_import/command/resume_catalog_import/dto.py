from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class ResumeCatalogImportResultDTO:
    """Возвращает состояние того же импорта после идемпотентного продолжения."""

    id: UUID
    status: str
    generation: int
