from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class VerifyConnectionResultDTO:
    """Возвращает результат сценария verify_connection."""

    channel_id: UUID
    revision: int
    job_id: UUID
