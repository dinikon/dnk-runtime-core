from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class CreateConnectionResultDTO:
    """Возвращает результат сценария create_connection."""

    channel_id: UUID
    connection_id: UUID
    revision: int
    verification_job_id: UUID
