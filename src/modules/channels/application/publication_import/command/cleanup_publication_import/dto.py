from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CleanupPublicationImportResultDTO:
    """Возвращает число освобождённых результатов подготовки."""

    released: int
