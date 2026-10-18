from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ApplyPublicationInitializationResultDTO:
    """Фиксирует результат apply_publication_initialization без пустого универсального DTO."""

    applied: bool
    complete: bool
    sequence: int
