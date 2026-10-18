from uuid import UUID
from datetime import datetime
from pydantic import BaseModel


class GetPublicationInitializationResponse(BaseModel):
    """Определяет отдельный HTTP-ответ сценария get_publication_initialization."""

    run_id: UUID | None
    connection_id: UUID
    status: str
    processed: int
    invalid: int
    sequence: int
    reason_code: str | None
    scope_limitations: tuple[str, ...]
    updated_at: datetime | None
    job_id: UUID | None
    read_complete: bool
    recovery_required: bool
