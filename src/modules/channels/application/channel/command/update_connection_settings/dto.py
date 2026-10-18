from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class UpdateConnectionSettingsResultDTO:
    """Возвращает результат сценария update_connection_settings."""

    channel_id: UUID
    connection_id: UUID
    revision: int
    verification_job_id: UUID | None
