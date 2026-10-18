from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class StartPublicationInitializationResultDTO:
    """Фиксирует результат start_publication_initialization без пустого универсального DTO."""

    run_id: UUID
    status: str
    job_id: UUID | None
